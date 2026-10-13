source "https://rubygems.org"

# Local preview matches production: GitHub Pages builds this site with its
# own pinned stack (Jekyll 3.x + allowlisted plugins — see
# https://pages.github.com/versions/), ignoring this Gemfile. Pinning to the
# github-pages gem keeps `bundle exec jekyll serve` honest about what ships.
gem "github-pages", group: :jekyll_plugins

# Ruby 3.4 dropped these from default gems; Jekyll 3.x still needs them.
gem "csv"
gem "base64"
gem "bigdecimal"
gem "logger"
gem "webrick"

platforms :mingw, :x64_mingw, :mswin, :jruby do
  gem "tzinfo", ">= 1", "< 3"
  gem "tzinfo-data"
end
gem "wdm", "~> 0.1.1", :platforms => [:mingw, :x64_mingw, :mswin]
gem "http_parser.rb", "~> 0.6.0", :platforms => [:jruby]
