#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
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
#
import os
import re
import cgi
import yaml
import markdown
from google.appengine.ext import webapp
from google.appengine.api import memcache
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from django.template import TemplateDoesNotExist

class opts:
  cache_time        = 1

class Article:
  def __init__(self, article_id):
    self.id = article_id
    raw = self.load()
    raw = raw.split("\n\n", 1)
    self.url = re.sub('-', '/', article_id, 3)
    self.meta = yaml.load(raw[0])
    self.summary = markdown.markdown(raw[1].split('~', 1)[0])
    self.body = markdown.markdown(raw[1])

  def load(self):
    article = memcache.get(self.id, 'article_')
    
    if article is None:
      try:
        static_article_path = os.path.join(os.path.dirname(__file__), 'articles/'+self.id)
        article = file(static_article_path, 'rb').read()
        memcache.set(self.id, article, opts.cache_time, 0, 'article_')
      except IOError: return
    
    return article
    
class Articles:
  def all(self):
    articles = []
    article_dir = os.path.join(os.path.dirname(__file__), 'articles/')
    for root, dirs, files in os.walk(article_dir, topdown=False):
      for name in files:
        article = Article(name)
        articles.append(article)
    return articles
  def filter(self, filters=None):
    return self.all()
    
class Index(webapp.RequestHandler):
  def get(self):
    articles = Articles().all()
    
    template_vars = {
      'articles' : articles
    }
    
    path = os.path.join(os.path.dirname(__file__), 'templates/pages/index.html')
    self.response.out.write(template.render(path, template_vars))
    
class ViewArticle(webapp.RequestHandler):
  def get(self, year, month, day, title):
    
    year        = cgi.escape(year)
    month       = cgi.escape(month)
    day         = cgi.escape(day)
    title       = cgi.escape(title)
    article_id  = year+'-'+month+'-'+day+'-'+title
    article     = Article(article_id)
      
    template_vars = { 'article' : article }
    
    path = os.path.join(os.path.dirname(__file__), 'templates/pages/article.html')
    self.response.out.write(template.render(path, template_vars))

class ViewArchives(webapp.RequestHandler):
  def get(self, year=None, month=None, day=None):
    
    articles = Articles().filter()
    template_vars = {
      'year'  : year,
      'month' : month,
      'day'   : day,
      'articles' : articles
    }
    path = os.path.join(os.path.dirname(__file__), 'templates/pages/archives.html')
    self.response.out.write(template.render(path, template_vars))

class ViewTag(webapp.RequestHandler):
  def get(self, tag):
    
    template_vars = { 'tag' : tag }
    
    path = os.path.join(os.path.dirname(__file__), 'templates/pages/tag.html')
    self.response.out.write(template.render(path, template_vars))

class RSS(webapp.RequestHandler):
  def get(self):
    path = os.path.join(os.path.dirname(__file__), 'templates/rss.feed')
    self.response.out.write(template.render(path, {}))

class Sitemap(webapp.RequestHandler):
  def get(self):
    articles = Articles().all()
    
    template_vars = {
      'articles' : articles
    }
    
    path = os.path.join(os.path.dirname(__file__), 'templates/sitemap.xml')
    self.response.out.write(template.render(path, template_vars))

class PageHandler(webapp.RequestHandler):
  def get(self, page):
    page = cgi.escape(page.replace('/', ''))
    try:
      path = os.path.join(os.path.dirname(__file__), 'templates/pages/'+page+'.html')
      self.response.out.write(template.render(path, {}))
    except TemplateDoesNotExist:
      path = os.path.join(os.path.dirname(__file__), 'templates/pages/404.html')
      self.response.out.write(template.render(path, {}))


      
def main():
  application = webapp.WSGIApplication(
  [
    ('/', Index),
    ('/(\d{4})/(\d{2})/(\d{2})/([^/]+)/?', ViewArticle),
    ('/archives/?([\d]{4})?/?([\d]{2})?/?([\d]{2})?/?', ViewArchives),
    ('/tag/([^/]+)', ViewTag),
    ('/rss', RSS),
    ('/sitemap', Sitemap),
    ('/(.*)/?', PageHandler)
  ], 
  debug=True)
  util.run_wsgi_app(application)

if __name__ == '__main__':
  main()