<%
  import os
  import sys

  import pdoc
  from pdoc.html_helpers import extract_toc, glimpse, to_html as _to_html, format_git_link

  import pyatv

  def link(d, name=None, fmt='{}'):
    name = fmt.format(name or d.qualname + ('()' if isinstance(d, pdoc.Function) else ''))
    if not isinstance(d, pdoc.Doc) or isinstance(d, pdoc.External) and not external_links:
        return name
    url = d.url(relative_to=module, link_prefix=link_prefix,
                top_ancestor=not show_inherited_members).replace("index.html", "").replace(".html", "")
    # Ugly, ugly hack to make navigation working in submodules...
    if url == "":
      url = ".."
    elif url.startswith("#"):
      pass
    elif "#" not in url:
      if not url.endswith("/"):
        url += "/"
    else:
        url = "../" + url
    return '<a title="{}" href="{}">{}</a>'.format(d.refname, url, name)

  def const_link(refname):
      desc = ".".join(refname.split(".")[-2:])
      return f'<a title="{refname}" href="/api/const#{refname}">{desc}</a>'

  def to_html(text):
    return _to_html(text, module=module, link=link, latex_math=latex_math)

  # Hack to convert Union[x, NoneType] to Optional[x] like in python 3.9
  def insert_union_types(returns, is_return=True):
    if "Union" in returns and "NoneType" in returns:
      returns = returns.replace("Union[", "Optional[")
      returns = returns.replace(",\N{NBSP}NoneType", "")
    return (' ->\N{NBSP}' if is_return else '') + returns
%>

<%def name="ident(name)"><span class="ident">${name}</span></%def>

<%def name="show_source(d)">
  % if (show_source_code or git_link_template) and d.source and d.obj is not getattr(d.inherits, 'obj', None):
    <% git_link = format_git_link(git_link_template, d) %>
    % if show_source_code:
      <details class="source">
        <summary>
            <span>Expand source code</span>
            % if git_link:
              <a href="${git_link}" class="git-link">View at GitHub</a>
            %endif
        </summary>
        <pre><code class="python">${d.source | h}</code></pre>
      </details>
    % elif git_link:
      <div class="git-link-div"><a href="${git_link}" class="git-link">Browse git</a></div>
    %endif
  %endif
</%def>

<%def name="show_desc(d, subclasses=None, short=False)">
  <%
  inherits = ' inherited' if d.inherits else ''
  docstring = glimpse(d.docstring) if short or inherits else d.docstring
  %>
  % if d.inherits:
      <p class="inheritance">
          <em>Inherited from:</em>
          % if hasattr(d.inherits, 'cls'):
              <code>${link(d.inherits.cls)}</code>.<code>${link(d.inherits, d.name)}</code>
          % else:
              <code>${link(d.inherits)}</code>
          % endif
      </p>
  % endif
  ${show_protocols(d, subclasses)}
  <section class="desc${inherits}">${docstring | to_html}</section>
  % if not isinstance(d, pdoc.Module):
  ${show_source(d)}
  % endif
</%def>

<%def name="show_module_list(modules)">
<h1>Python module list</h1>

% if not modules:
  <p>No modules found.</p>
% else:
  <dl id="http-server-module-list">
  % for name, desc in modules:
      <div class="flex">
      <dt><a href="${link_prefix}${name}">${name}</a></dt>
      <dd>${desc | glimpse, to_html}</dd>
      </div>
  % endfor
  </dl>
% endif
</%def>

<%def name="show_column_list(items)">
  <%
      two_column = len(items) >= 6 and all(len(i.name) < 20 for i in items)
  %>
  <ul class="${'two-column' if two_column else ''}">
  % for item in items:
    <li><code>${link(item, item.name)}</code></li>
  % endfor
  </ul>
</%def>

<%def name="show_protocols(f, subclasses)">
  <%
  feature_name = getattr(f.obj, "_feature_name", "")
  refname = "pyatv.const.FeatureName." + feature_name
  protocols = []
  proto_map = {proto.name.lower(): proto for proto in pyatv.const.Protocol}
  %>
  % if feature_name:
      % for subclass in subclasses or []:
          <%
          # Get reference to method/property in protocol implementation
          module_name, name = subclass.qualname.rsplit(".", maxsplit=1)
          module = sys.modules[module_name]
          method = getattr(getattr(module, name), f.name)

          # If method is a property, extract the getter method
          target = getattr(method, "fget", method)
          if target != f.obj and "facade" not in module.__name__:
              protocols.append(proto_map[module.__name__.split(".")[-1]])
          %>
      % endfor
      <div class="api_feature">
          <span>Feature: ${const_link(refname)},</span>
          <span>Supported by: ${", ".join([const_link(f"pyatv.const.Protocol.{x.name}") for x in protocols])}</span>
      </div>
  %endif
</%def>

<%def name="show_module(module)">
  <%
  variables = module.variables(sort=sort_identifiers)
  classes = module.classes(sort=sort_identifiers)
  functions = module.functions(sort=sort_identifiers)
  submodules = module.submodules()
  %>

  <%def name="show_func(f, subclasses)">
    <dt id="${f.refname}">
        <code class="name flex">
        <%
            params = ', '.join([insert_union_types(param, is_return=False) for param in f.params(annotate=show_type_annotations, link=link)])
            returns = show_type_annotations and f.return_annotation(link=link) or ''
            if returns:
                returns = insert_union_types(returns)
        %>
        <span>${f.funcdef()} ${ident(f.name)}</span>(<span>${params})${returns}</span>
        </code>
    </dt>
    <dd>
        ${show_desc(f, subclasses)}
    </dd>
  </%def>

  <header>
  % if http_server:
    <nav class="http-server-breadcrumbs">
      <a href="/">All packages</a>
      <% parts = module.name.split('.')[:-1] %>
      % for i, m in enumerate(parts):
        <% parent = '.'.join(parts[:i+1]) %>
        :: <a href="/${parent.replace('.', '/')}/">${parent}</a>
      % endfor
    </nav>
  % endif
  <h1 class="title">${'Namespace' if module.is_namespace else 'Module'} <code>${module.name}</code></h1>
  </header>

  <section id="section-intro">
  ${module.docstring | to_html}
  ${show_source(module)}
  </section>

  <section>
    % if submodules:
    <h2 class="section-title" id="header-submodules">Sub-modules</h2>
    <dl>
    % for m in submodules:
      <dt><code class="name">${link(m)}</code></dt>
      <dd>${show_desc(m, short=True)}</dd>
    % endfor
    </dl>
    % endif
  </section>

  <section>
    % if variables:
    <h2 class="section-title" id="header-variables">Global variables</h2>
    <dl>
    % for v in variables:
      <dt id="${v.refname}"><code class="name">var ${ident(v.name)}</code></dt>
      <dd>${show_desc(v)}</dd>
    % endfor
    </dl>
    % endif
  </section>

  <section>
    % if functions:
    <h2 class="section-title" id="header-functions">Functions</h2>
    <dl>
    % for f in functions:
      ${show_func(f, [])}
    % endfor
    </dl>
    % endif
  </section>

  <section>
    % if classes:
    <h2 class="section-title" id="header-classes">Classes</h2>
    <dl>
    % for c in classes:
      <%
      class_vars = c.class_variables(show_inherited_members, sort=sort_identifiers)
      smethods = c.functions(show_inherited_members, sort=sort_identifiers)
      inst_vars = c.instance_variables(show_inherited_members, sort=sort_identifiers)
      methods = c.methods(show_inherited_members, sort=sort_identifiers)
      mro = c.mro()
      subclasses = c.subclasses()
      params = ', '.join([insert_union_types(param, is_return=False) for param in c.params(annotate=show_type_annotations, link=link)])
      %>
      <dt id="${c.refname}"><code class="flex name class">
          <span>class ${ident(c.name)}</span>
          % if params:
              <span>(</span><span>${params})</span>
          % endif
      </code></dt>

      <dd>${show_desc(c)}

      % if mro:
          <h3>Ancestors</h3>
          <ul class="hlist">
          % for cls in mro:
              <li>${link(cls)}</li>
          % endfor
          </ul>
      %endif

      % if subclasses:
          <h3>Subclasses</h3>
          <ul class="hlist">
          % for sub in subclasses:
              <li>${link(sub)}</li>
          % endfor
          </ul>
      % endif
      % if class_vars:
          <h3>Class variables</h3>
          <dl>
          % for v in class_vars:
              <%
                  var_type = show_type_annotations and v.type_annotation(link=link) or ''
                  if var_type:
                      var_type = insert_union_types(var_type)

                  # Try to extract value from enums and pydantic models
                  var_value = ""
                  if any(cls.name.startswith("enum.") for cls in mro):
                    var_value = f" = {getattr(c.obj, v.name).value}"
                  elif any(cls.name.startswith("pydantic.main.BaseModel") for cls in mro):
                    if hasattr(c.obj, "__fields__"):
                      field_info = c.obj.__fields__[v.name]
                    else:
                      field_info = c.obj.model_fields[v.name]

                    # Ignore fields that are pydantic models as they produce unnecessary output
                    if "__pydantic_serializer__" not in dir(field_info.annotation):
                      var_value = f" = {field_info.default}"
              %>
              <dt id="${v.refname}"><code class="name">var ${ident(v.name)}${var_type}${var_value}</code></dt>
              <dd>${show_desc(v)}</dd>
          % endfor
          </dl>
      % endif
      % if smethods:
          <h3>Static methods</h3>
          <dl>
          % for f in smethods:
              ${show_func(f, subclasses)}
          % endfor
          </dl>
      % endif
      % if inst_vars:
          <h3>Instance variables</h3>
          <dl>
          % for v in inst_vars:
              <%
                  var_type = show_type_annotations and v.type_annotation(link=link) or ''
                  if var_type:
                      var_type = insert_union_types(var_type)
              %>
              <dt id="${v.refname}"><code class="name">var ${ident(v.name)}${var_type}</code></dt>
              <dd>${show_desc(v, subclasses)}</dd>
          % endfor
          </dl>
      % endif
      % if methods:
          <h3>Methods</h3>
          <dl>
          % for f in methods:
              ${show_func(f, subclasses)}
          % endfor
          </dl>
      % endif

      % if not show_inherited_members:
          <%
              members = c.inherited_members()
          %>
          % if members:
              <h3>Inherited members</h3>
              <ul class="hlist">
              % for cls, mems in members:
                  <li><code><b>${link(cls)}</b></code>:
                      <ul class="hlist">
                          % for m in mems:
                              <li><code>${link(m, name=m.name)}</code></li>
                          % endfor
                      </ul>

                  </li>
              % endfor
              </ul>
          % endif
      % endif

      </dd>
    % endfor
    </dl>
    % endif
  </section>
</%def>

<%def name="module_index(module)">
  <%
  variables = module.variables(sort=sort_identifiers)
  classes = module.classes(sort=sort_identifiers)
  functions = module.functions(sort=sort_identifiers)
  submodules = module.submodules()
  supermodule = module.supermodule
  %>
  <nav id="sidebar">

    <h1>Index</h1>
    ${extract_toc(module.docstring) if extract_module_toc_into_sidebar else ''}

    % if "__pdoc_dev_page__" in dir(module.obj):
    This module has additional documentation
    <a title="test" href=${f"{module.obj.__pdoc_dev_page__}"}>here</a>.
    % endif

    <ul id="index">
    % if supermodule:
    <li><h3>Super-module</h3>
      <ul>
        <li><code>${link(supermodule)}</code></li>
      </ul>
    </li>
    % endif

    % if submodules:
    <li><h3><a href="#header-submodules">Sub-modules</a></h3>
      <ul>
      % for m in submodules:
        <li><code>${link(m)}</code></li>
      % endfor
      </ul>
    </li>
    % endif

    % if variables:
    <li><h3><a href="#header-variables">Global variables</a></h3>
      ${show_column_list(variables)}
    </li>
    % endif

    % if functions:
    <li><h3><a href="#header-functions">Functions</a></h3>
      ${show_column_list(functions)}
    </li>
    % endif

    % if classes:
    <li><h3><a href="#header-classes">Classes</a></h3>
      <ul>
      % for c in classes:
        <li>
        <h4><code>${link(c)}</code></h4>
        <%
            members = c.functions(sort=sort_identifiers) + c.methods(sort=sort_identifiers)
            if list_class_variables_in_index:
                members += (c.instance_variables(sort=sort_identifiers) +
                            c.class_variables(sort=sort_identifiers))
            if not show_inherited_members:
                members = [i for i in members if not i.inherits]
            if sort_identifiers:
              members = sorted(members)
        %>
        % if members:
          ${show_column_list(members)}
        % endif
        </li>
      % endfor
      </ul>
    </li>
    % endif

    </ul>
  </nav>
</%def>

<%
url = module.name.replace("pyatv", "").replace(".", "/")
if url.startswith("/"):
  url = url[1:]
if not url.endswith("/"):
  url += "/"
%>

---
layout: template
title: API - ${module.name}
permalink: /api/${url}
link_group: api
---

% if module_list:
  <article id="content">
    ${show_module_list(modules)}
  </article>
% else:
  ${module_index(module)}
  <article id="content">
    ${show_module(module)}
  </article>
% endif

<footer id="footer">
    <p>Generated by <a href="https://pdoc3.github.io/pdoc"><cite>pdoc</cite>.</p>
</footer>
