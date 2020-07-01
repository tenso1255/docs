# Lint as: python3
# Copyright 2015 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Turn Python docstrings into Markdown for TensorFlow documentation."""

import ast
import collections
import enum
import functools
import inspect
import itertools
import json
import os
import re
import textwrap
import typing

from typing import Any, Dict, List, Tuple, Iterable, NamedTuple, Optional, Union

import astor

from tensorflow_docs.api_generator import doc_controls

from google.protobuf.message import Message as ProtoMessage


class ObjType(enum.Enum):
  """Enum to standardize object type checks."""
  TYPE_ALIAS = 'type_alias'
  MODULE = 'module'
  CLASS = 'class'
  CALLABLE = 'callable'
  PROPERTY = 'property'
  OTHER = 'other'


def get_obj_type(py_obj: Any) -> ObjType:
  """Get the `ObjType` for the `py_object`."""
  if hasattr(py_obj, '__args__') and hasattr(py_obj, '__origin__'):
    return ObjType.TYPE_ALIAS
  elif inspect.ismodule(py_obj):
    return ObjType.MODULE
  elif inspect.isclass(py_obj):
    return ObjType.CLASS
  elif callable(py_obj):
    return ObjType.CALLABLE
  elif isinstance(py_obj, property):
    return ObjType.PROPERTY
  else:
    return ObjType.OTHER


class ParserConfig(object):
  """Stores all indexes required to parse the docs."""

  def __init__(self, reference_resolver, duplicates, duplicate_of, tree, index,
               reverse_index, base_dir, code_url_prefix):
    """Object with the common config for docs_for_object() calls.

    Args:
      reference_resolver: An instance of ReferenceResolver.
      duplicates: A `dict` mapping fully qualified names to a set of all aliases
        of this name. This is used to automatically generate a list of all
        aliases for each name.
      duplicate_of: A map from duplicate names to preferred names of API
        symbols.
      tree: A `dict` mapping a fully qualified name to the names of all its
        members. Used to populate the members section of a class or module page.
      index: A `dict` mapping full names to objects.
      reverse_index: A `dict` mapping object ids to full names.
      base_dir: A base path that is stripped from file locations written to the
        docs.
      code_url_prefix: A Url to pre-pend to the links to file locations.
    """
    self.reference_resolver = reference_resolver
    self.duplicates = duplicates
    self.duplicate_of = duplicate_of
    self.tree = tree
    self.reverse_index = reverse_index
    self.index = index
    self.base_dir = base_dir
    self.code_url_prefix = code_url_prefix

  def py_name_to_object(self, full_name):
    """Return the Python object for a Python symbol name."""
    return self.index[full_name]


class _FileLocation(object):
  """This class indicates that the object is defined in a regular file.

  This can be used for the `defined_in` slot of the `PageInfo` objects.
  """
  GITHUB_LINE_NUMBER_TEMPLATE = '#L{start_line:d}-L{end_line:d}'

  def __init__(self, rel_path, url=None, start_line=None, end_line=None):
    self.rel_path = rel_path
    self.url = url
    self.start_line = start_line
    self.end_line = end_line

    github_main_re = 'github.com.*?(blob|tree)/master'
    suffix = ''
    # Only attach a line number for github URLs that are not using "main"
    if self.start_line and not re.search(github_main_re, self.url):
      if 'github.com' in self.url:
        suffix = self.GITHUB_LINE_NUMBER_TEMPLATE.format(
            start_line=self.start_line, end_line=self.end_line)

        self.url = self.url + suffix


def is_class_attr(full_name, index):
  """Check if the object's parent is a class.

  Args:
    full_name: The full name of the object, like `tf.module.symbol`.
    index: The {full_name:py_object} dictionary for the public API.

  Returns:
    True if the object is a class attribute.
  """
  parent_name = full_name.rsplit('.', 1)[0]
  if inspect.isclass(index[parent_name]):
    return True

  return False


class TFDocsError(Exception):
  pass


def documentation_path(full_name, is_fragment=False):
  """Returns the file path for the documentation for the given API symbol.

  Given the fully qualified name of a library symbol, compute the path to which
  to write the documentation for that symbol (relative to a base directory).
  Documentation files are organized into directories that mirror the python
  module/class structure.

  Args:
    full_name: Fully qualified name of a library symbol.
    is_fragment: If `False` produce a direct markdown link (`tf.a.b.c` -->
      `tf/a/b/c.md`). If `True` produce fragment link, `tf.a.b.c` -->
      `tf/a/b.md#c`

  Returns:
    The file path to which to write the documentation for `full_name`.
  """
  parts = full_name.split('.')
  if is_fragment:
    parts, fragment = parts[:-1], parts[-1]

  result = os.path.join(*parts) + '.md'

  if is_fragment:
    result = result + '#' + fragment

  return result


def _get_raw_docstring(py_object):
  """Get the docs for a given python object.

  Args:
    py_object: A python object to retrieve the docs for (class, function/method,
      or module).

  Returns:
    The docstring, or the empty string if no docstring was found.
  """

  if get_obj_type(py_object) is ObjType.TYPE_ALIAS:
    if inspect.getdoc(py_object) != inspect.getdoc(py_object.__origin__):
      result = inspect.getdoc(py_object)
    else:
      result = ''
  elif get_obj_type(py_object) is not ObjType.OTHER:
    result = inspect.getdoc(py_object) or ''
  else:
    result = ''

  result = _StripTODOs()(result)
  result = _StripPylints()(result)
  result = _AddDoctestFences()(result + '\n')
  return result


class _AddDoctestFences(object):
  """Adds ``` fences around doctest caret blocks >>> that don't have them."""
  CARET_BLOCK_RE = re.compile(
      r"""
    (?<=\n)\ *\n                           # After a blank line.
    (?P<indent>\ *)(?P<content>\>\>\>.*?)  # Whitespace and a triple caret.
    \n\s*?(?=\n|$)                         # Followed by a blank line""",
      re.VERBOSE | re.DOTALL)

  def _sub(self, match):
    groups = match.groupdict()
    fence = f"\n{groups['indent']}```\n"

    content = groups['indent'] + groups['content']
    return ''.join([fence, content, fence])

  def __call__(self, content):
    return self.CARET_BLOCK_RE.sub(self._sub, content)


class _StripTODOs(object):
  TODO_RE = re.compile('#? *TODO.*')

  def __call__(self, content: str) -> str:
    return self.TODO_RE.sub('', content)


class _StripPylints(object):
  PYLINT_RE = re.compile('# *?pylint:.*')

  def __call__(self, content: str) -> str:
    return self.PYLINT_RE.sub('', content)


class IgnoreLineInBlock(object):
  """Ignores the lines in a block.

  Attributes:
    block_start: Contains the start string of a block to ignore.
    block_end: Contains the end string of a block to ignore.
  """

  def __init__(self, block_start, block_end):
    self._block_start = block_start
    self._block_end = block_end
    self._in_block = False

    self._start_end_regex = re.escape(self._block_start) + r'.*?' + re.escape(
        self._block_end)

  def __call__(self, line):
    # If start and end block are on the same line, return True.
    if re.match(self._start_end_regex, line):
      return True

    if not self._in_block:
      if self._block_start in line:
        self._in_block = True

    elif self._block_end in line:
      self._in_block = False
      # True is being returned here because the last line in the block should
      # also be ignored.
      return True

    return self._in_block


# ?P<...> helps to find the match by entering the group name instead of the
# index. For example, instead of doing match.group(1) we can do
# match.group('brackets')
AUTO_REFERENCE_RE = re.compile(
    r"""
    (?P<brackets>\[.*?\])                    # find characters inside '[]'
    |
    `(?P<backticks>[\w\(\[\)\]\{\}.,=\s]+?)` # or find characters inside '``'
    """,
    flags=re.VERBOSE)


class ReferenceResolver(object):
  """Class for replacing `tf.symbol` references with Markdown links."""

  def __init__(self, duplicate_of, is_fragment, py_module_names):
    """Initializes a Reference Resolver.

    Args:
      duplicate_of: A map from duplicate names to preferred names of API
        symbols.
      is_fragment: A map from full names to bool for each symbol. If True the
        object lives at a page fragment `tf.a.b.c` --> `tf/a/b#c`. If False
        object has a page to itself: `tf.a.b.c` --> `tf/a/b/c`.
      py_module_names: A list of string names of Python modules.
    """
    self._duplicate_of = duplicate_of
    self._is_fragment = is_fragment
    self._all_names = set(is_fragment.keys())
    self._py_module_names = py_module_names
    self._partial_symbols_dict = self._create_partial_symbols_dict()

  @classmethod
  def from_visitor(cls, visitor, **kwargs):
    """A factory function for building a ReferenceResolver from a visitor.

    Args:
      visitor: an instance of `DocGeneratorVisitor`
      **kwargs: all remaining args are passed to the constructor

    Returns:
      an instance of `ReferenceResolver` ()
    """
    is_fragment = {}
    for full_name, obj in visitor.index.items():
      obj_type = get_obj_type(obj)
      if obj_type in (ObjType.CLASS, ObjType.MODULE):
        is_fragment[full_name] = False
      elif obj_type in (ObjType.CALLABLE, ObjType.TYPE_ALIAS):
        if is_class_attr(full_name, visitor.index):
          is_fragment[full_name] = True
        else:
          is_fragment[full_name] = False
      else:
        is_fragment[full_name] = True

    return cls(
        duplicate_of=visitor.duplicate_of, is_fragment=is_fragment, **kwargs)

  def is_fragment(self, full_name: str):
    """Returns True if the object's doc is a subsection of another page."""
    return self._is_fragment[full_name]

  @classmethod
  def from_json_file(cls, filepath):
    """Initialize the reference resolver via _api_cache.json."""
    with open(filepath) as f:
      json_dict = json.load(f)

    return cls(**json_dict)

  def _partial_symbols(self, symbol):
    """Finds the partial symbols given the true symbol.

    For example, symbol: `tf.keras.layers.Conv2D`, then the partial dictionary
    returned will be:

    partials = ["tf.keras.layers.Conv2D","keras.layers.Conv2D","layers.Conv2D"]

    There should at least be one '.' in the partial symbol generated so as to
    avoid guessing for the true symbol.

    Args:
      symbol: String, representing the true symbol.

    Returns:
      A list of partial symbol names
    """

    split_symbol = symbol.split('.')
    partials = [
        '.'.join(split_symbol[i:]) for i in range(1,
                                                  len(split_symbol) - 1)
    ]
    return partials

  def _create_partial_symbols_dict(self):
    """Creates a partial symbols dictionary for all the symbols in TensorFlow.

    Returns:
      A dictionary mapping {partial_symbol: real_symbol}
    """
    partial_symbols_dict = collections.defaultdict(list)

    for name in sorted(self._all_names):
      if 'tf.compat.v' in name or 'tf.contrib' in name:
        continue
      partials = self._partial_symbols(name)
      for partial in partials:
        partial_symbols_dict[partial].append(name)

    new_partial_dict = {}
    for partial, full_names in partial_symbols_dict.items():
      if not full_names:
        continue

      full_names = [
          self._duplicate_of.get(full_name, full_name)
          for full_name in full_names
      ]

      new_partial_dict[partial] = full_names[0]

    return new_partial_dict

  def to_json_file(self, filepath):
    """Converts the RefenceResolver to json and writes it to the specified file.

    Args:
      filepath: The file path to write the json to.
    """

    try:
      os.makedirs(os.path.dirname(filepath))
    except OSError:
      pass

    json_dict = {}
    for key, value in self.__dict__.items():
      # Drop these fields, they are generated by the constructor.
      if key == '_all_names' or key == '_partial_symbols_dict':
        continue

      # Strip off any leading underscores on field names as these are not
      # recognized by the constructor.
      json_dict[key.lstrip('_')] = value

    with open(filepath, 'w') as f:
      json.dump(json_dict, f, indent=2, sort_keys=True)
      f.write('\n')

  def replace_references(self, string, relative_path_to_root, full_name=None):
    """Replace `tf.symbol` references with links to symbol's documentation page.

    This function finds all occurrences of "`tf.symbol`" in `string`
    and replaces them with markdown links to the documentation page
    for "symbol".

    `relative_path_to_root` is the relative path from the document
    that contains the "`tf.symbol`" reference to the root of the API
    documentation that is linked to. If the containing page is part of
    the same API docset, `relative_path_to_root` can be set to
    `os.path.dirname(documentation_path(name))`, where `name` is the
    python name of the object whose documentation page the reference
    lives on.

    Args:
      string: A string in which "`tf.symbol`" references should be replaced.
      relative_path_to_root: The relative path from the containing document to
        the root of the API documentation that is being linked to.
      full_name: (optional) The full name of current object, so replacements can
        depend on context.

    Returns:
      `string`, with "`tf.symbol`" references replaced by Markdown links.
    """

    def one_ref(match):
      return self._one_ref(match, relative_path_to_root, full_name)

    fixed_lines = []

    filters = [
        IgnoreLineInBlock('<pre class="tfo-notebook-code-cell-output">',
                          '</pre>'),
        IgnoreLineInBlock('```', '```')
    ]

    for line in string.splitlines():
      if not any(filter_block(line) for filter_block in filters):
        line = re.sub(AUTO_REFERENCE_RE, one_ref, line)
      fixed_lines.append(line)

    return '\n'.join(fixed_lines)

  def python_link(self,
                  link_text,
                  ref_full_name,
                  relative_path_to_root,
                  code_ref=True):
    """Resolve a "`tf.symbol`" reference to a Markdown link.

    This will pick the canonical location for duplicate symbols.  The
    input to this function should already be stripped of the '@' and
    '{}'.  This function returns a Markdown link. If `code_ref` is
    true, it is assumed that this is a code reference, so the link
    text will be rendered as code (using backticks).
    `link_text` should refer to a library symbol, starting with 'tf.'.

    Args:
      link_text: The text of the Markdown link.
      ref_full_name: The fully qualified name of the symbol to link to.
      relative_path_to_root: The relative path from the location of the current
        document to the root of the API documentation.
      code_ref: If true (the default), put `link_text` in `...`.

    Returns:
      A markdown link to the documentation page of `ref_full_name`.
    """
    url = self.reference_to_url(ref_full_name, relative_path_to_root)

    if code_ref:
      link_text = link_text.join(['<code>', '</code>'])
    else:
      link_text = self._link_text_to_html(link_text)

    return f'<a href="{url}">{link_text}</a>'

  @staticmethod
  def _link_text_to_html(link_text):
    code_re = '`(.*?)`'
    return re.sub(code_re, r'<code>\1</code>', link_text)

  def py_main_name(self, full_name):
    """Return the main name for a Python symbol name."""
    return self._duplicate_of.get(full_name, full_name)

  def reference_to_url(self, ref_full_name, relative_path_to_root):
    """Resolve a "`tf.symbol`" reference to a relative path.

    The input to this function should already be stripped of the '@'
    and '{}', and its output is only the link, not the full Markdown.

    If `ref_full_name` is the name of a class member, method, or property, the
    link will point to the page of the containing class, and it will include the
    method name as an anchor. For example, `tf.module.MyClass.my_method` will be
    translated into a link to
    `os.join.path(relative_path_to_root, 'tf/module/MyClass.md#my_method')`.

    Args:
      ref_full_name: The fully qualified name of the symbol to link to.
      relative_path_to_root: The relative path from the location of the current
        document to the root of the API documentation.

    Returns:
      A relative path that links from the documentation page of `from_full_name`
      to the documentation page of `ref_full_name`.

    Raises:
      TFDocsError: If the symbol is not found.
    """
    if self._is_fragment.get(ref_full_name, False):
      # methods and constants get duplicated. And that's okay.
      # Use the main name of their parent.
      parent_name, short_name = ref_full_name.rsplit('.', 1)
      parent_main_name = self._duplicate_of.get(parent_name, parent_name)
      main_name = '.'.join([parent_main_name, short_name])
    else:
      main_name = self._duplicate_of.get(ref_full_name, ref_full_name)

    # Check whether this link exists
    if main_name not in self._all_names:
      raise TFDocsError(f'Cannot make link to {main_name!r}: Not in index.')

    ref_path = documentation_path(main_name, self._is_fragment[main_name])
    return os.path.join(relative_path_to_root, ref_path)

  def _one_ref(self, match, relative_path_to_root, full_name=None):
    """Return a link for a single "`tf.symbol`" reference."""

    if match.group(1):
      # Found a '[]' group, return it unmodified.
      return match.group('brackets')

    # Found a '``' group.
    string = match.group('backticks')

    link_text = string

    string = re.sub(r'(.*)[\(\[].*', r'\1', string)

    if string.startswith('compat.v1') or string.startswith('compat.v2'):
      string = 'tf.' + string
    elif string.startswith('v1') or string.startswith('v2'):
      string = 'tf.compat.' + string

    elif full_name is None or ('tf.compat.v' not in full_name and
                               'tf.contrib' not in full_name):
      string = self._partial_symbols_dict.get(string, string)

    try:
      if string.startswith('tensorflow::'):
        # C++ symbol
        return self._cc_link(string, link_text, relative_path_to_root)

      is_python = False
      for py_module_name in self._py_module_names:
        if string == py_module_name or string.startswith(py_module_name + '.'):
          is_python = True
          break

      if is_python:  # Python symbol
        return self.python_link(
            link_text, string, relative_path_to_root, code_ref=True)
    except TFDocsError:
      pass

    return match.group(0)

  def _cc_link(self, string, link_text, relative_path_to_root):
    """Generate a link for a `tensorflow::...` reference."""
    # TODO(joshl): Fix this hard-coding of paths.
    if string == 'tensorflow::ClientSession':
      ret = 'class/tensorflow/client-session.md'
    elif string == 'tensorflow::Scope':
      ret = 'class/tensorflow/scope.md'
    elif string == 'tensorflow::Status':
      ret = 'class/tensorflow/status.md'
    elif string == 'tensorflow::Tensor':
      ret = 'class/tensorflow/tensor.md'
    elif string == 'tensorflow::ops::Const':
      ret = 'namespace/tensorflow/ops.md#const'
    else:
      raise TFDocsError(f'C++ reference not understood: "{string}"')

    # relative_path_to_root gets you to api_docs/python, we go from there
    # to api_docs/cc, and then add ret.
    cc_relative_path = os.path.normpath(
        os.path.join(relative_path_to_root, '../cc', ret))

    return f'<a href="{cc_relative_path}"><code>{link_text}</code></a>'


def _handle_compatibility(doc) -> Tuple[str, Dict[str, str]]:
  """Parse and remove compatibility blocks from the main docstring.

  Args:
    doc: The docstring that contains compatibility notes.

  Returns:
    A tuple of the modified doc string and a hash that maps from compatibility
    note type to the text of the note.
  """
  compatibility_notes = {}
  match_compatibility = re.compile(r'[ \t]*@compatibility\((\w+)\)\s*\n'
                                   r'((?:[^@\n]*\n)+)'
                                   r'\s*@end_compatibility')
  for f in match_compatibility.finditer(doc):
    compatibility_notes[f.group(1)] = f.group(2)
  return match_compatibility.subn(r'', doc)[0], compatibility_notes


def _pairs(items):
  """Given an list of items [a,b,a,b...], generate pairs [(a,b),(a,b)...].

  Args:
    items: A list of items (length must be even)

  Returns:
    A list of pairs.
  """
  assert len(items) % 2 == 0
  return list(zip(items[::2], items[1::2]))


class TitleBlock(object):
  """A class to parse title blocks (like `Args:`) and convert them to markdown.

  This handles the "Args/Returns/Raises" blocks and anything similar.

  These are used to extract metadata (argument descriptions, etc), and upgrade
  This `TitleBlock` to markdown.

  These blocks are delimited by indentation. There must be a blank line before
  the first `TitleBlock` in a series.

  The expected format is:

  ```
  Title:
    Freeform text
    arg1: value1
    arg2: value1
  ```

  These are represented as:

  ```
  TitleBlock(
    title = "Arguments",
    text = "Freeform text",
    items=[('arg1', 'value1'), ('arg2', 'value2')])
  ```

  The "text" and "items" fields may be empty. When both are empty the generated
  markdown only serves to upgrade the title to a <h4>.

  Attributes:
    title: The title line, without the colon.
    text: Freeform text. Anything between the `title`, and the `items`.
    items: A list of (name, value) string pairs. All items must have the same
      indentation.
  """

  _INDENTATION_REMOVAL_RE = re.compile(r'( *)(.+)')

  # Don't change the width="214px" without consulting with the devsite-team.
  _TABLE_TEMPLATE = textwrap.dedent("""
    <!-- Tabular view -->
     <table class="responsive fixed orange">
    <colgroup><col width="214px"><col></colgroup>
    <tr><th colspan="2">{title}</th></tr>
    {text}
    {items}
    </table>
    """)

  _ITEMS_TEMPLATE = textwrap.dedent("""\
    <tr>
    <td>
    {name}
    </td>
    <td>
    {description}
    </td>
    </tr>""")

  _TEXT_TEMPLATE = textwrap.dedent("""\
    <tr class="alt">
    <td colspan="2">
    {text}
    </td>
    </tr>""")

  def __init__(self,
               *,
               title: Optional[str] = None,
               text: str,
               items: Iterable[Tuple[str, str]]):
    self.title = title
    self.text = text
    self.items = items

  def table_view(self, title_template: Optional[str] = None) -> str:
    """Returns a tabular markdown version of the TitleBlock.

    Tabular view is only for `Args`, `Returns`, `Raises` and `Attributes`. If
    anything else is encountered, redirect to list view.

    Args:
      title_template: Template for title detailing how to display it.

    Returns:
      Table containing the content to display.
    """

    if title_template is not None:
      title = title_template.format(title=self.title)
    else:
      title = self.title

    text = self.text.strip()
    if text:
      text = self._TEXT_TEMPLATE.format(text=text)
      text = self._INDENTATION_REMOVAL_RE.sub(r'\2', text)

    items = []
    for name, description in self.items:
      if not description:
        description = ''
      else:
        description = description.strip()
      item_table = self._ITEMS_TEMPLATE.format(
          name=f'`{name}`', description=description)
      item_table = self._INDENTATION_REMOVAL_RE.sub(r'\2', item_table)
      items.append(item_table)

    return '\n' + self._TABLE_TEMPLATE.format(
        title=title, text=text, items=''.join(items)) + '\n'

  def list_view(self, title_template: str) -> str:
    """Returns a List markdown version of the TitleBlock.

    Args:
      title_template: Template for title detailing how to display it.

    Returns:
      Markdown list containing the content to display.
    """

    sub = []
    sub.append(title_template.format(title=self.title))
    sub.append(textwrap.dedent(self.text))
    sub.append('\n')

    for name, description in self.items:
      description = description.strip()
      if not description:
        sub.append(f'* <b>`{name}`</b>\n')
      else:
        sub.append(f'* <b>`{name}`</b>: {description}\n')

    return ''.join(sub)

  # This regex matches an entire title-block.
  BLOCK_RE = re.compile(
      r"""
      (?:^|^\n|\n\n)                  # After a blank line (non-capturing):
        (?P<title>[A-Z][\s\w]{0,20})  # Find a sentence case title, followed by
          \s*:\s*?(?=\n)              # whitespace, a colon and a new line.
      (?P<content>.*?)                # Then take everything until
        (?=\n\S|$)                    # look ahead finds a non-indented line
                                      # (a new-line followed by non-whitespace)
    """, re.VERBOSE | re.DOTALL)

  # This
  ITEM_RE = re.compile(
      r"""
      ^(\*?\*?          # Capture optional *s to allow *args, **kwargs.
          \w[\w.]*?     # Capture a word character followed by word characters
                        # or "."s.
      )\s*:\s           # Allow any whitespace around the colon.""",
      re.MULTILINE | re.VERBOSE)

  @classmethod
  def split_string(cls, docstring: str):
    r"""Given a docstring split it into a list of `str` or `TitleBlock` chunks.

    For example the docstring of `tf.nn.relu`:

    '''
    Computes `max(features, 0)`.

    Args:
      features: A `Tensor`. Must be one of the following types: `float32`,
        `float64`, `int32`, `int64`, `uint8`, `int16`, `int8`, `uint16`, `half`.
      name: A name for the operation (optional).

    More freeform markdown text.
    '''

    This is parsed, and returned as:

    ```
    [
        "Computes rectified linear: `max(features, 0)`.",
        TitleBlock(
          title='Args',
          text='',
          items=[
            ('features', ' A `Tensor`. Must be...'),
            ('name', ' A name for the operation (optional).\n\n')]
        ),
        "More freeform markdown text."
    ]
    ```
    Args:
      docstring: The docstring to parse

    Returns:
      The docstring split into chunks. Each chunk produces valid markdown when
      `str` is called on it (each chunk is a python `str`, or a `TitleBlock`).
    """
    parts = []
    while docstring:
      split = re.split(cls.BLOCK_RE, docstring, maxsplit=1)
      # The first chunk in split is all text before the TitleBlock.
      before = split.pop(0)
      parts.append(before)

      # If `split` is empty, there were no other matches, and we're done.
      if not split:
        break

      # If there was a match,  split contains three items. The two capturing
      # groups in the RE, and the remainder.
      title, content, docstring = split

      # Now `content` contains the text and the name-value item pairs.
      # separate these two parts.
      content = textwrap.dedent(content)
      split = cls.ITEM_RE.split(content)
      text = split.pop(0)
      items = _pairs(split)

      title_block = cls(title=title, text=text, items=items)
      parts.append(title_block)

    return parts


class _DocstringInfo(typing.NamedTuple):
  brief: str
  docstring_parts: List[Union[TitleBlock, str]]
  compatibility: Dict[str, str]


def _parse_md_docstring(py_object, relative_path_to_root, full_name,
                        reference_resolver) -> _DocstringInfo:
  """Parse the object's docstring and return a `_DocstringInfo`.

  This function clears @@'s from the docstring, and replaces `` references
  with markdown links.

  For links within the same set of docs, the `relative_path_to_root` for a
  docstring on the page for `full_name` can be set to:

  ```python
  relative_path_to_root = os.path.relpath(
    path='.', start=os.path.dirname(documentation_path(full_name)) or '.')
  ```

  Args:
    py_object: A python object to retrieve the docs for (class, function/method,
      or module).
    relative_path_to_root: The relative path from the location of the current
      document to the root of the Python API documentation. This is used to
      compute links for "`tf.symbol`" references.
    full_name: (optional) The api path to the current object, so replacements
      can depend on context.
    reference_resolver: An instance of ReferenceResolver.

  Returns:
    A _DocstringInfo object, all fields will be empty if no docstring was found.
  """
  # TODO(wicke): If this is a partial, use the .func docstring and add a note.
  raw_docstring = _get_raw_docstring(py_object)

  raw_docstring = reference_resolver.replace_references(raw_docstring,
                                                        relative_path_to_root,
                                                        full_name)

  atat_re = re.compile(r' *@@[a-zA-Z_.0-9]+ *$')
  raw_docstring = '\n'.join(
      line for line in raw_docstring.split('\n') if not atat_re.match(line))

  docstring, compatibility = _handle_compatibility(raw_docstring)

  if 'Generated by: tensorflow/tools/api/generator' in docstring:
    docstring = ''

  # Remove the first-line "brief" docstring.
  lines = docstring.split('\n')
  brief = lines.pop(0)

  docstring = '\n'.join(lines)

  docstring_parts = TitleBlock.split_string(docstring)

  return _DocstringInfo(brief, docstring_parts, compatibility)


class TypeAnnotationExtractor(ast.NodeVisitor):
  """Extracts the type annotations by parsing the AST of a function."""

  def __init__(self):
    self.annotation_dict = {}
    self.arguments_typehint_exists = False
    self.return_typehint_exists = False

  def visit_FunctionDef(self, node) -> None:  # pylint: disable=invalid-name
    """Visits the `FunctionDef` node in AST tree and extracts the typehints."""

    # Capture the return type annotation.
    if node.returns:
      self.annotation_dict['return'] = astor.to_source(
          node.returns).strip().replace('"""', '"')
      self.return_typehint_exists = True

    # Capture the args type annotation.
    for arg in node.args.args:
      if arg.annotation:
        self.annotation_dict[arg.arg] = astor.to_source(
            arg.annotation).strip().replace('"""', '"')
        self.arguments_typehint_exists = True

    # Capture the kwarg only args type annotation.
    for kwarg in node.args.kwonlyargs:
      if kwarg.annotation:
        self.annotation_dict[kwarg.arg] = astor.to_source(
            kwarg.annotation).strip().replace('"""', '"')
        self.arguments_typehint_exists = True


class ASTDefaultValueExtractor(ast.NodeVisitor):
  """Extracts the default values by parsing the AST of a function."""

  _PAREN_NUMBER_RE = re.compile(r'^\(([0-9.e-]+)\)')

  def __init__(self):
    self.ast_args_defaults = []
    self.ast_kw_only_defaults = []

  def _preprocess(self, val: str) -> str:
    text_default_val = astor.to_source(val).strip().replace(
        '\t', '\\t').replace('\n', '\\n').replace('"""', "'")
    text_default_val = self._PAREN_NUMBER_RE.sub('\\1', text_default_val)
    return text_default_val

  def visit_FunctionDef(self, node) -> None:  # pylint: disable=invalid-name
    """Visits the `FunctionDef` node and extracts the default values."""

    for default_val in node.args.defaults:
      if default_val is not None:
        text_default_val = self._preprocess(default_val)
        self.ast_args_defaults.append(text_default_val)

    for default_val in node.args.kw_defaults:
      if default_val is not None:
        text_default_val = self._preprocess(default_val)
        self.ast_kw_only_defaults.append(text_default_val)


class FormatArguments(object):
  """Formats the arguments and adds type annotations if they exist."""

  _INTERNAL_NAMES = {
      'ops.GraphKeys': 'tf.GraphKeys',
      '_ops.GraphKeys': 'tf.GraphKeys',
      'init_ops.zeros_initializer': 'tf.zeros_initializer',
      'init_ops.ones_initializer': 'tf.ones_initializer',
      'saver_pb2.SaverDef': 'tf.train.SaverDef',
  }

  _OBJECT_MEMORY_ADDRESS_RE = re.compile(r'<(?P<type>.+) object at 0x[\da-f]+>')

  # A regular expression capturing a python identifier.
  _IDENTIFIER_RE = r'[a-zA-Z_]\w*'

  _INDIVIDUAL_TYPES_RE = re.compile(
      r"""
        (?P<single_type>
          ([\w.]*)
          (?=$|,| |\]|\[)
        )
      """, re.IGNORECASE | re.VERBOSE)

  _TYPING = frozenset(
      list(typing.__dict__.keys()) +
      ['int', 'str', 'bytes', 'float', 'complex', 'bool', 'None'])

  _IMMUTABLE_TYPES = frozenset(
      [int, str, bytes, float, complex, bool,
       type(None), tuple, frozenset])

  def __init__(
      self,
      type_annotations: Dict[str, str],
      parser_config: ParserConfig,
      func_full_name: str,
  ) -> None:
    self._type_annotations = type_annotations
    self._reverse_index = parser_config.reverse_index
    self._reference_resolver = parser_config.reference_resolver
    # func_full_name is used to calculate the relative path.
    self._func_full_name = func_full_name

    self._is_fragment = self._reference_resolver._is_fragment.get(
        self._func_full_name, None)

  def _calc_relative_path(self, single_type: str) -> str:
    """Calculates the relative path of the type from the function.

    The number of `..` are counted from `os.path.relpath` and adjusted based
    on if the function (for which signature is being generated) is a fragment
    or not.

    Args:
      single_type: The type for which the relative path is calculated.

    Returns:
      Relative path consisting of only `..` as a path.
    """

    func_full_path = self._func_full_name.replace('.', '/')
    single_type = single_type.replace('.', '/')

    dot_count = os.path.relpath(single_type, func_full_path).count('..')
    # Methods are fragments, stand-alone functions are not.
    if self._is_fragment:
      dot_count -= 2
    else:
      dot_count -= 1

    dot_list = ['..'] * dot_count
    return os.path.join(*dot_list)  # pylint: disable=no-value-for-parameter

  def _get_link(self, full_name: str, ast_typehint: str) -> str:
    full_name = self._reference_resolver._duplicate_of.get(full_name, full_name)  # pylint: disable=protected-access
    relative_path = self._calc_relative_path(ast_typehint)
    url = os.path.join(relative_path, full_name.replace('.', '/')) + '.md'
    # Use `full_name` for the text in the link since its available over
    # `ast_typehint`.
    return f'<a href="{url}"><code>{full_name}</code></a>'

  def _extract_non_builtin_types(self, arg_obj: Any,
                                 non_builtin_types: List[Any]) -> List[Any]:
    """Extracts the non-builtin types from a type annotations object.

    Recurses if an object contains `__args__` attribute. If an object is
    an inbuilt object or an `Ellipsis` then its skipped.

    Args:
      arg_obj: Type annotation object.
      non_builtin_types: List to keep track of the non-builtin types extracted.

    Returns:
      List of non-builtin types.
    """

    annotations = getattr(arg_obj, '__args__', [arg_obj])
    if annotations is None:
      annotations = [arg_obj]

    for anno in annotations:
      if self._reverse_index.get(id(anno), None):
        non_builtin_types.append(anno)
      elif (anno in self._IMMUTABLE_TYPES or anno in typing.__dict__.values() or
            anno is Ellipsis):
        continue
      elif hasattr(anno, '__args__'):
        self._extract_non_builtin_types(anno, non_builtin_types)
      else:
        non_builtin_types.append(anno)
    return non_builtin_types

  def _get_non_builtin_ast_types(self, ast_typehint: str) -> List[str]:
    """Extracts non-builtin types from a string AST type annotation.

    If the type is an inbuilt type or an `...`(Ellipsis) then its skipped.

    Args:
      ast_typehint: AST extracted type annotation.

    Returns:
      List of non-builtin ast types.
    """

    non_builtin_ast_types = []
    for single_type, _ in self._INDIVIDUAL_TYPES_RE.findall(ast_typehint):
      if (not single_type or single_type in self._TYPING or
          single_type == '...'):
        continue
      non_builtin_ast_types.append(single_type)
    return non_builtin_ast_types

  def _linkify(self, non_builtin_map: Dict[str, Any], match) -> str:
    """Links off to types that can be linked.

    Args:
      non_builtin_map: Dictionary mapping non-builtin_ast_types to
        non_builtin_type_objs
      match: Match object returned by `re.sub`.

    Returns:
      Linked type annotation if the type annotation object exists.
    """

    group = match.groupdict()
    ast_single_typehint = group['single_type']

    # If the AST type hint is a built-in type hint or an `Ellipsis`,
    # return it as is.
    if ast_single_typehint not in non_builtin_map:
      return ast_single_typehint

    if not non_builtin_map:
      return ast_single_typehint

    # Get the type object from the ast_single_typehint and lookup the object
    # in reverse_index to get its full name.
    obj_full_name = self._reverse_index.get(
        id(non_builtin_map[ast_single_typehint]), None)
    if obj_full_name is None:
      return ast_single_typehint

    return self._get_link(obj_full_name, ast_single_typehint)

  def _preprocess(self, ast_typehint: str, obj_anno: Any) -> str:
    """Links type annotations to its page if it exists.

    Args:
      ast_typehint: AST extracted type annotation.
      obj_anno: Type annotation object.

    Returns:
      Linked type annotation if the type annotation object exists.
    """
    # If the object annotations exists in the reverse_index, get the link
    # directly for the entire annotation.
    obj_anno_full_name = self._reverse_index.get(id(obj_anno), None)
    if obj_anno_full_name is not None:
      return self._get_link(obj_anno_full_name, ast_typehint)

    non_builtin_ast_types = self._get_non_builtin_ast_types(ast_typehint)
    try:
      non_builtin_type_objs = self._extract_non_builtin_types(obj_anno, [])
    except RecursionError:
      non_builtin_type_objs = {}

    # If the length doesn't match then don't linkify any type annotation. This
    # is done to avoid linking to wrong pages instead of guessing.
    if len(non_builtin_type_objs) != len(non_builtin_ast_types):
      non_builtin_map = {}
    else:
      non_builtin_map = dict(zip(non_builtin_ast_types, non_builtin_type_objs))

    partial_func = functools.partial(self._linkify, non_builtin_map)
    return self._INDIVIDUAL_TYPES_RE.sub(partial_func, ast_typehint)

  def _replace_internal_names(self, default_text: str) -> str:
    full_name_re = f'^{self._IDENTIFIER_RE}(.{self._IDENTIFIER_RE})+'
    match = re.match(full_name_re, default_text)
    if match:
      for internal_name, public_name in self._INTERNAL_NAMES.items():
        if match.group(0).startswith(internal_name):
          return public_name + default_text[len(internal_name):]
    return default_text

  def format_return(self, return_anno: Any) -> str:
    return self._preprocess(self._type_annotations['return'], return_anno)

  def format_args(self, args: List[inspect.Parameter]) -> List[str]:
    """Creates a text representation of the args in a method/function.

    Args:
      args: List of args to format.

    Returns:
      Formatted args with type annotations if they exist.
    """

    args_text_repr = []

    for arg in args:
      arg_name = arg.name
      if arg_name in self._type_annotations:
        typeanno = self._preprocess(self._type_annotations[arg_name],
                                    arg.annotation)
        args_text_repr.append(f'{arg_name}: {typeanno}')
      else:
        args_text_repr.append(f'{arg_name}')

    return args_text_repr

  def format_kwargs(self, kwargs: List[inspect.Parameter],
                    ast_defaults: List[str]) -> List[str]:
    """Creates a text representation of the kwargs in a method/function.

    Args:
      kwargs: List of kwargs to format.
      ast_defaults: Default values extracted from the function's AST tree.

    Returns:
      Formatted kwargs with type annotations if they exist.
    """

    kwargs_text_repr = []

    if len(ast_defaults) < len(kwargs):
      ast_defaults.extend([None] * (len(kwargs) - len(ast_defaults)))

    for kwarg, ast_default in zip(kwargs, ast_defaults):
      kname = kwarg.name
      default_val = kwarg.default

      if id(default_val) in self._reverse_index:
        default_text = self._reverse_index[id(default_val)]
      elif ast_default is not None:
        default_text = ast_default
        if default_text != repr(default_val):
          default_text = self._replace_internal_names(default_text)
      # Kwarg without default value.
      elif default_val is kwarg.empty:
        kwargs_text_repr.extend(self.format_args([kwarg]))
        continue
      else:
        # Strip object memory addresses to avoid unnecessary doc churn.
        default_text = self._OBJECT_MEMORY_ADDRESS_RE.sub(
            r'<\g<type>>', repr(default_val))

      # Format the kwargs to add the type annotation and default values.
      if kname in self._type_annotations:
        typeanno = self._preprocess(self._type_annotations[kname],
                                    kwarg.annotation)
        kwargs_text_repr.append(f'{kname}: {typeanno} = {default_text}')
      else:
        kwargs_text_repr.append(f'{kname}={default_text}')

    return kwargs_text_repr


class _SignatureComponents(NamedTuple):
  """Contains the components that make up the signature of a function/method."""

  arguments: List[str]
  arguments_typehint_exists: bool
  return_typehint_exists: bool
  return_type: Optional[str] = None

  def __str__(self):
    arguments_signature = ''
    if self.arguments:
      str_signature = ',\n'.join(self.arguments)
      # If there is no type annotation on arguments, then wrap the entire
      # signature to width 80.
      if not self.arguments_typehint_exists:
        str_signature = textwrap.fill(str_signature, width=80)
      arguments_signature = '\n' + textwrap.indent(
          str_signature, prefix='    ') + '\n'

    full_signature = f'({arguments_signature})'
    if self.return_typehint_exists:
      full_signature += f' -> {self.return_type}'

    return full_signature


def generate_signature(func: Any, parser_config: ParserConfig,
                       func_full_name: str) -> _SignatureComponents:
  """Given a function, returns a list of strings representing its args.

  This function uses `__name__` for callables if it is available. This can lead
  to poor results for functools.partial and other callable objects.

  The returned string is Python code, so if it is included in a Markdown
  document, it should be typeset as code (using backticks), or escaped.

  Args:
    func: A function, method, or functools.partial to extract the signature for.
    parser_config: `ParserConfig` for the method/function whose signature is
      generated.
    func_full_name: The full name of a function whose signature is generated.

  Returns:
    A `_SignatureComponents` NamedTuple.
  """

  all_args_list = []

  try:
    sig = inspect.signature(func)
    sig_values = sig.parameters.values()
    return_anno = sig.return_annotation
  except (ValueError, TypeError):
    sig_values = []
    return_anno = None

  type_annotation_visitor = TypeAnnotationExtractor()
  ast_defaults_visitor = ASTDefaultValueExtractor()

  try:
    func_source = textwrap.dedent(inspect.getsource(func))
    func_ast = ast.parse(func_source)
    # Extract the type annotation from the parsed ast.
    type_annotation_visitor.visit(func_ast)
    ast_defaults_visitor.visit(func_ast)
  except Exception:  # pylint: disable=broad-except
    # A wide-variety of errors can be thrown here.
    pass

  type_annotations = type_annotation_visitor.annotation_dict
  arguments_typehint_exists = type_annotation_visitor.arguments_typehint_exists
  return_typehint_exists = type_annotation_visitor.return_typehint_exists

  #############################################################################
  # Process the information about the func.
  #############################################################################

  pos_only_args = []
  args = []
  kwargs = []
  only_kwargs = []
  varargs = None
  varkwargs = None
  skip_self_cls = True

  for index, param in enumerate(sig_values):
    kind = param.kind
    default = param.default

    if skip_self_cls and param.name in ('self', 'cls', '_cls'):
      # Only skip the first parameter. If the function contains both
      # `self` and `cls`, skip only the first one.
      skip_self_cls = False
    elif kind == param.POSITIONAL_ONLY:
      pos_only_args.append(param)
    elif default is param.empty and kind == param.POSITIONAL_OR_KEYWORD:
      args.append(param)
    elif default is not param.empty and kind == param.POSITIONAL_OR_KEYWORD:
      kwargs.append(param)
    elif kind == param.VAR_POSITIONAL:
      varargs = (index, param)
    elif kind == param.KEYWORD_ONLY:
      only_kwargs.append(param)
    elif kind == param.VAR_KEYWORD:
      varkwargs = param

  #############################################################################
  # Build the text representation of Args and Kwargs.
  #############################################################################

  formatter = FormatArguments(
      type_annotations, parser_config, func_full_name=func_full_name)

  if pos_only_args:
    all_args_list.extend(formatter.format_args(pos_only_args))
    all_args_list.append('/')

  if args:
    all_args_list.extend(formatter.format_args(args))

  if kwargs:
    all_args_list.extend(
        formatter.format_kwargs(kwargs, ast_defaults_visitor.ast_args_defaults))

  if only_kwargs:
    if varargs is None:
      all_args_list.append('*')
    all_args_list.extend(
        formatter.format_kwargs(only_kwargs,
                                ast_defaults_visitor.ast_kw_only_defaults))

  if varargs is not None:
    all_args_list.insert(varargs[0], '*' + varargs[1].name)

  if varkwargs is not None:
    all_args_list.append('**' + varkwargs.name)

  if return_anno and return_anno is not sig.empty and type_annotations.get(
      'return', None):
    return_type = formatter.format_return(return_anno)
  else:
    return_type = 'None'

  return _SignatureComponents(
      arguments=all_args_list,
      arguments_typehint_exists=arguments_typehint_exists,
      return_typehint_exists=return_typehint_exists,
      return_type=return_type)


def _get_defining_class(py_class, name):
  for cls in inspect.getmro(py_class):
    if name in cls.__dict__:
      return cls
  return None


class MemberInfo(NamedTuple):
  """Describes an attribute of a class or module."""
  short_name: str
  full_name: str
  obj: Any
  doc: _DocstringInfo
  url: str


class MethodInfo(NamedTuple):
  """Described a method."""
  short_name: str
  full_name: str
  obj: Any
  doc: _DocstringInfo
  url: str
  signature: _SignatureComponents
  decorators: List[str]
  defined_in: Optional[_FileLocation]

  @classmethod
  def from_member_info(cls, method_info: MemberInfo,
                       signature: _SignatureComponents, decorators: List[str],
                       defined_in: Optional[_FileLocation]):
    """Upgrades a `MemberInfo` to a `MethodInfo`."""
    return cls(
        **method_info._asdict(),
        signature=signature,
        decorators=decorators,
        defined_in=defined_in)


def extract_decorators(func: Any) -> List[str]:
  """Extracts the decorators on top of functions/methods.

  Args:
    func: The function to extract the decorators from.

  Returns:
    A List of decorators.
  """

  class ASTDecoratorExtractor(ast.NodeVisitor):

    def __init__(self):
      self.decorator_list = []

    def visit_FunctionDef(self, node):  # pylint: disable=invalid-name
      for dec in node.decorator_list:
        self.decorator_list.append(astor.to_source(dec).strip())

  visitor = ASTDecoratorExtractor()

  try:
    func_source = textwrap.dedent(inspect.getsource(func))
    func_ast = ast.parse(func_source)
    visitor.visit(func_ast)
  except Exception:  # pylint: disable=broad-except
    # A wide-variety of errors can be thrown here.
    pass

  return visitor.decorator_list


class PageInfo(object):
  """Base-class for api_pages objects.

  Converted to markdown by pretty_docs.py.

  Attributes:
    full_name: The full, main name, of the object being documented.
    short_name: The last part of the full name.
    py_object: The object being documented.
    defined_in: A _FileLocation describing where the object was defined.
    aliases: A list of full-name for all aliases for this object.
    doc: A list of objects representing the docstring. These can all be
      converted to markdown using str().
  """

  def __init__(self, full_name, py_object):
    """Initialize a PageInfo.

    Args:
      full_name: The full, main name, of the object being documented.
      py_object: The object being documented.
    """
    self.full_name = full_name
    self.py_object = py_object

    self._defined_in = None
    self._aliases = None
    self._doc = None

  @property
  def short_name(self):
    """Returns the documented object's short name."""
    return self.full_name.split('.')[-1]

  @property
  def defined_in(self):
    """Returns the path to the file where the documented object is defined."""
    return self._defined_in

  def set_defined_in(self, defined_in):
    """Sets the `defined_in` path."""
    assert self.defined_in is None
    self._defined_in = defined_in

  @property
  def aliases(self):
    """Returns a list of all full names for the documented object."""
    return self._aliases

  def set_aliases(self, aliases):
    """Sets the `aliases` list.

    Args:
      aliases: A list of strings. Containing all the object's full names.
    """
    assert self.aliases is None
    self._aliases = aliases

  @property
  def doc(self) -> _DocstringInfo:
    """Returns a `_DocstringInfo` created from the object's docstring."""
    return self._doc

  def set_doc(self, doc: _DocstringInfo):
    """Sets the `doc` field.

    Args:
      doc: An instance of `_DocstringInfo`.
    """
    assert self.doc is None
    self._doc = doc


class FunctionPageInfo(PageInfo):
  """Collects docs For a function Page.

  Attributes:
    full_name: The full, main name, of the object being documented.
    short_name: The last part of the full name.
    py_object: The object being documented.
    defined_in: A _FileLocation describing where the object was defined.
    aliases: A list of full-name for all aliases for this object.
    doc: A list of objects representing the docstring. These can all be
      converted to markdown using str().
    signature: the parsed signature (see: generate_signature)
    decorators: A list of decorator names.
  """

  def __init__(self, full_name, py_object):
    """Initialize a FunctionPageInfo.

    Args:
      full_name: The full, main name, of the object being documented.
      py_object: The object being documented.
    """
    super(FunctionPageInfo, self).__init__(full_name, py_object)

    self._signature = None
    self._decorators = []

  @property
  def signature(self):
    return self._signature

  def collect_docs(self, parser_config):
    """Collect all information necessary to genertate the function page.

    Mainly this is details about the function signature.

    Args:
      parser_config: The ParserConfig for the module being documented.
    """

    assert self.signature is None
    self._signature = generate_signature(self.py_object, parser_config,
                                         self.full_name)
    self._decorators = extract_decorators(self.py_object)

  @property
  def decorators(self):
    return list(self._decorators)

  def add_decorator(self, dec):
    self._decorators.append(dec)

  def get_metadata_html(self):
    return Metadata(self.full_name).build_html()


class TypeAliasPageInfo(PageInfo):
  """Collects docs For a type alias page.

  Attributes:
    full_name: The full, main name, of the object being documented.
    short_name: The last part of the full name.
    py_object: The object being documented.
    defined_in: A _FileLocation describing where the object was defined.
    aliases: A list of full-name for all aliases for this object.
    doc: A list of objects representing the docstring. These can all be
      converted to markdown using str().
    signature: the parsed signature (see: generate_signature)
    decorators: A list of decorator names.
  """

  def __init__(self, full_name: str, py_object: Any) -> None:
    """Initialize a `TypeAliasPageInfo`.

    Args:
      full_name: The full, main name, of the object being documented.
      py_object: The object being documented.
    """

    super().__init__(full_name, py_object)
    self._signature = None

  @property
  def signature(self) -> None:
    return self._signature

  def collect_docs(self, parser_config) -> None:
    """Collect all information necessary to genertate the function page.

    Mainly this is details about the function signature.

    Args:
      parser_config: The ParserConfig for the module being documented.
    """
    del parser_config

    assert self.signature is None
    wrapped_sig = textwrap.fill(
        repr(self.py_object).replace('typing.', ''), width=80)
    self._signature = textwrap.indent(wrapped_sig, '    ').strip()

  def get_metadata_html(self) -> str:
    return Metadata(self.full_name).build_html()


class ClassPageInfo(PageInfo):
  """Collects docs for a class page.

  Attributes:
    full_name: The full, main name, of the object being documented.
    short_name: The last part of the full name.
    py_object: The object being documented.
    defined_in: A _FileLocation describing where the object was defined.
    aliases: A list of full-name for all aliases for this object.
    doc: A list of objects representing the docstring. These can all be
      converted to markdown using str().
    attributes: A dict mapping from "name" to a docstring
    bases: A list of `MemberInfo` objects pointing to the docs for the parent
      classes.
    methods: A list of `MethodInfo` objects documenting the class' methods.
    classes: A list of `MemberInfo` objects pointing to docs for any nested
      classes.
    other_members: A list of `MemberInfo` objects documenting any other object's
      defined inside the class object (mostly enum style fields).
    attr_block: A `TitleBlock` containing information about the Attributes of
      the class.
  """

  def __init__(self, full_name, py_object):
    """Initialize a ClassPageInfo.

    Args:
      full_name: The full, main name, of the object being documented.
      py_object: The object being documented.
    """
    super(ClassPageInfo, self).__init__(full_name, py_object)

    self._namedtuplefields = collections.OrderedDict()
    if issubclass(py_object, tuple):
      namedtuple_attrs = ('_asdict', '_fields', '_make', '_replace')
      if all(hasattr(py_object, attr) for attr in namedtuple_attrs):
        for name in py_object._fields:
          self._namedtuplefields[name] = None

    self._properties = collections.OrderedDict()
    self._bases = None
    self._methods = []
    self._classes = []
    self._other_members = []
    self.attr_block = None

  @property
  def bases(self):
    """Returns a list of `MemberInfo` objects pointing to the class' parents."""
    return self._bases

  def set_attr_block(self, attr_block):
    assert self.attr_block is None
    self.attr_block = attr_block

  def _set_bases(self, relative_path, parser_config):
    """Builds the `bases` attribute, to document this class' parent-classes.

    This method sets the `bases` to a list of `MemberInfo` objects point to the
    doc pages for the class' parents.

    Args:
      relative_path: The relative path from the doc this object describes to the
        documentation root.
      parser_config: An instance of `ParserConfig`.
    """
    bases = []
    obj = parser_config.py_name_to_object(self.full_name)
    for base in obj.__bases__:
      base_full_name = parser_config.reverse_index.get(id(base), None)
      if base_full_name is None:
        continue
      base_doc = _parse_md_docstring(base, relative_path, self.full_name,
                                     parser_config.reference_resolver)
      base_url = parser_config.reference_resolver.reference_to_url(
          base_full_name, relative_path)

      link_info = MemberInfo(
          short_name=base_full_name.split('.')[-1],
          full_name=base_full_name,
          obj=base,
          doc=base_doc,
          url=base_url)
      bases.append(link_info)

    self._bases = bases

  def _add_property(self, member_info: MemberInfo):
    """Adds an entry to the `properties` list.

    Args:
      member_info: a `MemberInfo` describing the property.
    """
    doc = member_info.doc
    # Hide useless namedtuple docs-trings.
    if re.match('Alias for field number [0-9]+', doc.brief):
      doc = doc._replace(docstring_parts=[], brief='')

    new_parts = [doc.brief]
    # Strip args/returns/raises from property
    new_parts.extend([
        str(part)
        for part in doc.docstring_parts
        if not isinstance(part, TitleBlock)
    ])
    new_parts = [textwrap.indent(part, '  ') for part in new_parts]
    new_parts.append('')
    desc = '\n'.join(new_parts)

    if member_info.short_name in self._namedtuplefields:
      self._namedtuplefields[member_info.short_name] = desc
    else:
      self._properties[member_info.short_name] = desc

  @property
  def methods(self):
    """Returns a list of `MethodInfo` describing the class' methods."""
    return self._methods

  def _add_method(
      self,
      member_info: MemberInfo,
      defining_class: Optional[type],  # pylint: disable=g-bare-generic
      parser_config: ParserConfig) -> None:
    """Adds a `MethodInfo` entry to the `methods` list.

    Args:
      member_info: a `MemberInfo` describing the method.
      defining_class: The `type` object where this method is defined.
      parser_config: A `ParserConfig`.
    """
    if defining_class is None:
      return

    # Omit methods defined by namedtuple.
    original_method = defining_class.__dict__[member_info.short_name]
    if (hasattr(original_method, '__module__') and
        (original_method.__module__ or '').startswith('namedtuple')):
      return

    # Some methods are often overridden without documentation. Because it's
    # obvious what they do, don't include them in the docs if there's no
    # docstring.
    if (not member_info.doc.brief.strip() and
        member_info.short_name in ['__del__', '__copy__']):
      return

    signature = generate_signature(member_info.obj, parser_config,
                                   member_info.full_name)

    decorators = extract_decorators(member_info.obj)

    defined_in = _get_defined_in(member_info.obj, parser_config)

    method_info = MethodInfo.from_member_info(member_info, signature,
                                              decorators, defined_in)
    self._methods.append(method_info)

  @property
  def classes(self):
    """Returns a list of `MemberInfo` pointing to any nested classes."""
    return self._classes

  def get_metadata_html(self) -> str:
    meta_data = Metadata(self.full_name)
    for item in itertools.chain(self.classes, self.methods, self.other_members):
      meta_data.append(item)

    return meta_data.build_html()

  def _add_class(self, member_info):
    """Adds a `MemberInfo` for a nested class to `classes` list.

    Args:
      member_info: a `MemberInfo` describing the class.
    """
    self._classes.append(member_info)

  @property
  def other_members(self):
    """Returns a list of `MemberInfo` describing any other contents."""
    return self._other_members

  def _add_other_member(self, member_info: MemberInfo):
    """Adds an `MemberInfo` entry to the `other_members` list.

    Args:
      member_info: a `MemberInfo` describing the object.
    """
    self._other_members.append(member_info)

  def _add_member(
      self,
      member_info: MemberInfo,
      defining_class: Optional[type],  # pylint: disable=g-bare-generic
      parser_config: ParserConfig,
  ) -> None:
    """Adds a member to the class page."""
    obj_type = get_obj_type(member_info.obj)

    if obj_type is ObjType.PROPERTY:
      self._add_property(member_info)
    elif obj_type is ObjType.CLASS:
      if defining_class is None:
        return
      self._add_class(member_info)
    elif obj_type is ObjType.CALLABLE:
      self._add_method(member_info, defining_class, parser_config)
    else:
      # Exclude members defined by protobuf that are useless
      if issubclass(self.py_object, ProtoMessage):
        if (member_info.short_name.endswith('_FIELD_NUMBER') or
            member_info.short_name in ['__slots__', 'DESCRIPTOR']):
          return

      self._add_other_member(member_info)

  def collect_docs(self, parser_config):
    """Collects information necessary specifically for a class's doc page.

    Mainly, this is details about the class's members.

    Args:
      parser_config: An instance of ParserConfig.
    """
    py_class = self.py_object
    doc_path = documentation_path(self.full_name)
    relative_path = os.path.relpath(
        path='.', start=os.path.dirname(doc_path) or '.')

    self._set_bases(relative_path, parser_config)

    for child_short_name in parser_config.tree[self.full_name]:
      child_full_name = '.'.join([self.full_name, child_short_name])
      child = parser_config.py_name_to_object(child_full_name)

      # Don't document anything that is defined in object or by protobuf.
      defining_class = _get_defining_class(py_class, child_short_name)
      if defining_class in [object, type, tuple, BaseException, Exception]:
        continue

      # The following condition excludes most protobuf-defined symbols.
      if (defining_class and
          defining_class.__name__ in ['CMessage', 'Message', 'MessageMeta']):
        continue

      if doc_controls.should_skip_class_attr(py_class, child_short_name):
        continue

      child_doc = _parse_md_docstring(child, relative_path, self.full_name,
                                      parser_config.reference_resolver)

      child_url = parser_config.reference_resolver.reference_to_url(
          child_full_name, relative_path)

      member_info = MemberInfo(child_short_name, child_full_name, child,
                               child_doc, child_url)
      self._add_member(member_info, defining_class, parser_config)

    self.set_attr_block(self._augment_attributes(self.doc.docstring_parts))

  def _augment_attributes(self,
                          docstring_parts: List[Any]) -> Optional[TitleBlock]:
    """Augments and deletes the "Attr" block of the docstring.

    The augmented block is returned and then added to the markdown page by
    pretty_docs.py. The existing Attribute block is deleted from the docstring.

    Merges `namedtuple` fields and properties into the attrs block.

    + `namedtuple` fields first, in order.
    + Then the docstring `Attr:` block.
    + Then any `properties` not mentioned above.

    Args:
      docstring_parts: A list of docstring parts.

    Returns:
      Augmented "Attr" block.
    """

    attribute_block = None

    for attr_block_index, part in enumerate(docstring_parts):
      if isinstance(part, TitleBlock) and part.title.startswith('Attr'):
        raw_attrs = collections.OrderedDict(part.items)
        break
    else:
      # Didn't find the attributes block, there may still be attributes so
      # add a placeholder for them at the end.
      raw_attrs = collections.OrderedDict()
      attr_block_index = len(docstring_parts)
      docstring_parts.append(None)

    attrs = collections.OrderedDict()
    # namedtuple fields first.
    attrs.update(self._namedtuplefields)
    # the contents of the `Attrs:` block from the docstring
    attrs.update(raw_attrs)
    # properties last.
    for name, desc in self._properties.items():
      # Don't overwrite existing items
      attrs.setdefault(name, desc)

    if attrs:
      attribute_block = TitleBlock(
          title='Attributes', text='', items=attrs.items())

    # Delete the Attrs block if it exists or delete the placeholder.
    del docstring_parts[attr_block_index]

    return attribute_block


class ModulePageInfo(PageInfo):
  """Collects docs for a module page.

  Attributes:
    full_name: The full, main name, of the object being documented.
    short_name: The last part of the full name.
    py_object: The object being documented.
    defined_in: A _FileLocation describing where the object was defined.
    aliases: A list of full-name for all aliases for this object.
    doc: A list of objects representing the docstring. These can all be
      converted to markdown using str().
    classes: A list of `MemberInfo` objects pointing to docs for the classes in
      this module.
    functions: A list of `MemberInfo` objects pointing to docs for the functions
      in this module
    modules: A list of `MemberInfo` objects pointing to docs for the modules in
      this module.
    type_alias: A list of `MemberInfo` objects pointing to docs for the type
      aliases in this module.
    other_members: A list of `MemberInfo` objects documenting any other object's
      defined on the module object (mostly enum style fields).
  """

  def __init__(self, full_name, py_object):
    """Initialize a `ModulePageInfo`.

    Args:
      full_name: The full, main name, of the object being documented.
      py_object: The object being documented.
    """
    super(ModulePageInfo, self).__init__(full_name, py_object)

    self._modules = []
    self._classes = []
    self._functions = []
    self._other_members = []
    self._type_alias = []

  @property
  def modules(self):
    return self._modules

  @property
  def functions(self):
    return self._functions

  @property
  def classes(self):
    return self._classes

  @property
  def type_alias(self):
    return self._type_alias

  @property
  def other_members(self):
    return self._other_members

  def _add_module(self, member_info: MemberInfo):
    self._modules.append(member_info)

  def _add_class(self, member_info: MemberInfo):
    self._classes.append(member_info)

  def _add_function(self, member_info: MemberInfo):
    self._functions.append(member_info)

  def _add_type_alias(self, member_info: MemberInfo):
    self._type_alias.append(member_info)

  def _add_other_member(self, member_info: MemberInfo):
    self._other_members.append(member_info)

  def get_metadata_html(self):
    meta_data = Metadata(self.full_name)

    # Objects with their own pages are not added to the metadata list for the
    # module, the module only has a link to the object page. No docs.
    for item in self.other_members:
      meta_data.append(item)

    return meta_data.build_html()

  def _add_member(self, member_info: MemberInfo) -> None:
    """Adds members of the modules to the respective lists."""
    obj_type = get_obj_type(member_info.obj)
    if obj_type is ObjType.MODULE:
      self._add_module(member_info)
    elif obj_type is ObjType.CLASS:
      self._add_class(member_info)
    elif obj_type is ObjType.CALLABLE:
      self._add_function(member_info)
    elif obj_type is ObjType.TYPE_ALIAS:
      self._add_type_alias(member_info)
    else:
      self._add_other_member(member_info)

  def collect_docs(self, parser_config):
    """Collect information necessary specifically for a module's doc page.

    Mainly this is information about the members of the module.

    Args:
      parser_config: An instance of ParserConfig.
    """
    relative_path = os.path.relpath(
        path='.',
        start=os.path.dirname(documentation_path(self.full_name)) or '.')

    member_names = parser_config.tree.get(self.full_name, [])
    for member_short_name in member_names:

      if member_short_name in [
          '__builtins__', '__doc__', '__file__', '__name__', '__path__',
          '__package__', '__cached__', '__loader__', '__spec__',
          'absolute_import', 'division', 'print_function', 'unicode_literals'
      ]:
        continue

      if self.full_name:
        member_full_name = self.full_name + '.' + member_short_name
      else:
        member_full_name = member_short_name

      member = parser_config.py_name_to_object(member_full_name)

      member_doc = _parse_md_docstring(member, relative_path, self.full_name,
                                       parser_config.reference_resolver)

      url = parser_config.reference_resolver.reference_to_url(
          member_full_name, relative_path)

      member_info = MemberInfo(member_short_name, member_full_name, member,
                               member_doc, url)
      self._add_member(member_info)


def docs_for_object(full_name, py_object, parser_config):
  """Return a PageInfo object describing a given object from the TF API.

  This function uses _parse_md_docstring to parse the docs pertaining to
  `object`.

  This function resolves '`tf.symbol`' references in the docstrings into links
  to the appropriate location. It also adds a list of alternative names for the
  symbol automatically.

  It assumes that the docs for each object live in a file given by
  `documentation_path`, and that relative links to files within the
  documentation are resolvable.

  Args:
    full_name: The fully qualified name of the symbol to be documented.
    py_object: The Python object to be documented. Its documentation is sourced
      from `py_object`'s docstring.
    parser_config: A ParserConfig object.

  Returns:
    Either a `FunctionPageInfo`, `ClassPageInfo`, or a `ModulePageInfo`
    depending on the type of the python object being documented.

  Raises:
    RuntimeError: If an object is encountered for which we don't know how
      to make docs.
  """

  # Which other aliases exist for the object referenced by full_name?
  main_name = parser_config.reference_resolver.py_main_name(full_name)
  duplicate_names = parser_config.duplicates.get(main_name, [])
  if main_name in duplicate_names:
    duplicate_names.remove(main_name)

  obj_type = get_obj_type(py_object)
  if obj_type is ObjType.CLASS:
    page_info = ClassPageInfo(main_name, py_object)
  elif obj_type is ObjType.CALLABLE:
    page_info = FunctionPageInfo(main_name, py_object)
  elif obj_type is ObjType.MODULE:
    page_info = ModulePageInfo(main_name, py_object)
  elif obj_type is ObjType.TYPE_ALIAS:
    page_info = TypeAliasPageInfo(main_name, py_object)
  else:
    raise RuntimeError('Cannot make docs for object {full_name}: {py_object!r}')

  relative_path = os.path.relpath(
      path='.', start=os.path.dirname(documentation_path(full_name)) or '.')

  page_info.set_doc(
      _parse_md_docstring(py_object, relative_path, full_name,
                          parser_config.reference_resolver))

  page_info.collect_docs(parser_config)

  page_info.set_aliases(duplicate_names)

  page_info.set_defined_in(_get_defined_in(py_object, parser_config))

  return page_info


def _unwrap_obj(obj):
  while True:
    unwrapped_obj = getattr(obj, '__wrapped__', None)
    if unwrapped_obj is None:
      break
    obj = unwrapped_obj
  return obj


def _get_defined_in(py_object: Any,
                    parser_config: ParserConfig) -> Optional[_FileLocation]:
  """Returns a description of where the passed in python object was defined.

  Args:
    py_object: The Python object.
    parser_config: A ParserConfig object.

  Returns:
    A `_FileLocation`
  """
  # Every page gets a note about where this object is defined
  base_dirs_and_prefixes = zip(parser_config.base_dir,
                               parser_config.code_url_prefix)
  try:
    obj_path = inspect.getfile(_unwrap_obj(py_object))
  except TypeError:  # getfile throws TypeError if py_object is a builtin.
    return None

  code_url_prefix = None
  for base_dir, temp_prefix in base_dirs_and_prefixes:

    rel_path = os.path.relpath(path=obj_path, start=base_dir)
    # A leading ".." indicates that the file is not inside `base_dir`, and
    # the search should continue.
    if rel_path.startswith('..'):
      continue
    else:
      code_url_prefix = temp_prefix
      break

  # No link if the file was not found in a `base_dir`, or the prefix is None.
  if code_url_prefix is None:
    return None

  try:
    lines, start_line = inspect.getsourcelines(py_object)
    end_line = start_line + len(lines) - 1
  except (IOError, TypeError, IndexError):
    start_line = None
    end_line = None

  # TODO(wicke): If this is a generated file, link to the source instead.
  # TODO(wicke): Move all generated files to a generated/ directory.
  # TODO(wicke): And make their source file predictable from the file name.

  # In case this is compiled, point to the original
  if rel_path.endswith('.pyc'):
    # If a PY3 __pycache__/ subdir is being used, omit it.
    rel_path = rel_path.replace('__pycache__' + os.sep, '')
    # Strip everything after the first . so that variants such as .pyc and
    # .cpython-3x.pyc or similar are all handled.
    rel_path = rel_path.partition('.')[0] + '.py'

  # Never include links outside this code base.
  if re.search(r'\b_api\b', rel_path):
    return None
  if re.search(r'\bapi/(_v2|_v1)\b', rel_path):
    return None
  if re.search(r'<[\w\s]+>', rel_path):
    # Built-ins emit paths like <embedded stdlib>, <string>, etc.
    return None
  if '<attrs generated' in rel_path:
    return None

  if re.match(r'.*/gen_[^/]*\.py$', rel_path):
    return _FileLocation(rel_path)
  if 'genfiles' in rel_path:
    return _FileLocation(rel_path)
  elif re.match(r'.*_pb2\.py$', rel_path):
    # The _pb2.py files all appear right next to their defining .proto file.

    rel_path = rel_path[:-7] + '.proto'
    return _FileLocation(
        rel_path=rel_path, url=os.path.join(code_url_prefix, rel_path))  # pylint: disable=undefined-loop-variable
  else:
    return _FileLocation(
        rel_path=rel_path,
        url=os.path.join(code_url_prefix, rel_path),
        start_line=start_line,
        end_line=end_line)  # pylint: disable=undefined-loop-variable


# TODO(markdaoust): This should just parse, pretty_docs should generate the md.
def generate_global_index(library_name, index, reference_resolver):
  """Given a dict of full names to python objects, generate an index page.

  The index page generated contains a list of links for all symbols in `index`
  that have their own documentation page.

  Args:
    library_name: The name for the documented library to use in the title.
    index: A dict mapping full names to python objects.
    reference_resolver: An instance of ReferenceResolver.

  Returns:
    A string containing an index page as Markdown.
  """
  symbol_links = []
  for full_name, py_object in index.items():
    obj_type = get_obj_type(py_object)
    if obj_type in (ObjType.OTHER, ObjType.PROPERTY):
      continue
    # In Python 3, unbound methods are functions, so eliminate those.
    if obj_type is ObjType.CALLABLE:
      if is_class_attr(full_name, index):
        continue
    symbol_links.append(
        (full_name, reference_resolver.python_link(full_name, full_name, '.')))

  lines = [f'# All symbols in {library_name}', '']

  # Sort all the symbols once, so that the ordering is preserved when its broken
  # up into main symbols and compat symbols and sorting the sublists is not
  # required.
  symbol_links = sorted(symbol_links, key=lambda x: x[0])

  compat_v1_symbol_links = []
  compat_v2_symbol_links = []
  primary_symbol_links = []

  for symbol, link in symbol_links:
    if symbol.startswith('tf.compat.v1'):
      if 'raw_ops' not in symbol:
        compat_v1_symbol_links.append(link)
    elif symbol.startswith('tf.compat.v2'):
      compat_v2_symbol_links.append(link)
    else:
      primary_symbol_links.append(link)

  lines.append('## Primary symbols')
  for link in primary_symbol_links:
    lines.append(f'*  {link}')

  if compat_v2_symbol_links:
    lines.append('\n## Compat v2 symbols\n')
    for link in compat_v2_symbol_links:
      lines.append(f'*  {link}')

  if compat_v1_symbol_links:
    lines.append('\n## Compat v1 symbols\n')
    for link in compat_v1_symbol_links:
      lines.append(f'*  {link}')

  # TODO(markdaoust): use a _ModulePageInfo -> prety_docs.build_md_page()
  return '\n'.join(lines)


class Metadata(object):
  """A class for building a page's Metadata block.

  Attributes:
    name: The name of the page being described by the Metadata block.
    version: The source version.
  """

  def __init__(self, name, version=None, content=None):
    """Creates a Metadata builder.

    Args:
      name: The name of the page being described by the Metadata block.
      version: The source version.
      content: Content to create the metadata from.
    """

    self.name = name

    self.version = version
    if self.version is None:
      self.version = 'Stable'

    self._content = content
    if self._content is None:
      self._content = []

  def append(self, item):
    """Adds an item from the page to the Metadata block.

    Args:
      item: The parsed page section to add.
    """
    self._content.append(item.short_name)

  def build_html(self):
    """Returns the Metadata block as an Html string."""
    # Note: A schema is not a URL. It is defined with http: but doesn't resolve.
    schema = 'http://developers.google.com/ReferenceObject'
    parts = [f'<div itemscope itemtype="{schema}">']

    parts.append(f'<meta itemprop="name" content="{self.name}" />')
    parts.append(f'<meta itemprop="path" content="{self.version}" />')
    for item in self._content:
      parts.append(f'<meta itemprop="property" content="{item}"/>')

    parts.extend(['</div>', ''])

    return '\n'.join(parts)
