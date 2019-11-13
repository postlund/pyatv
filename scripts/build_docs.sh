#!/bin/sh

run()
{
    docker run -p 4000:4000 --rm \
               -v "$PWD:/srv/jekyll" \
               -v "$PWD/docs/vendor/bundle:/usr/local/bundle" \
               -w /srv/jekyll/docs \
               -it jekyll/jekyll:3.8 "$@"
}

run bundle update github-pages

if [ "$1" = "build" ]; then
    run jekyll build
elif [ "$1" = "serve" ]; then
    run jekyll serve --incremental --watch
else
   echo "!!! Unknown command! Use build or serve!" >&2
   exit 1
fi
