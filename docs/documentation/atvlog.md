---
layout: template
title: atvlog
permalink: /documentation/atvlog/
link_group: documentation
---
# Table of Contents
{:.no_toc}
* TOC
{:toc}

# atvlog

The `atvlog` script simplifies log inspection by generating an HTML file with basic
live filtering capabilities.

*Note: This is an incubating script and may change behavior with short notice.*

# Features

Log output from the following tools are supported as input:

* atvremote and atvscript
* Home Assistant log

A special `markdown` mode is supported, which extracts a log from the following
format:

~~~
text here is ignored
```log
log data here
```
also ignored
~~~

Filtering can be performed on the following attributes:

* Include entries based on regexp
* Exclude entries based on regexp (performed prior to include regexp)
* Log levels
* Date can be stripped for more compact log

# Serving output via web server

It is possible to serve the generated log output via a built in web server using flag `-w`:

```shell
$ atvlog -w pyatv.log
Press ENTER to quit
```

Then visit `http://<ip>:8008` to see the log. The port number can be changed
with `-p xxxx`.

# Examples

```shell
$ atvlog pyatv.log  # Print output to stdout
$ atvlog --output pyatv.html pyatv.log
$ cat pyatv.log | atvlog -  # Read from stdin
$ cat markdown.log | atvlog --format=markdown -
```

