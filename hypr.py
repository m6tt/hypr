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
import config
from google.appengine.ext import webapp
from google.appengine.api import memcache
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from django.template import TemplateDoesNotExist

class Article:
  def __init__(self, article_id):
    self.id       = re.sub('.md', '', article_id)
    self.id       = re.sub('.txt', '', article_id)
    self.raw      = self.load()
    if self.raw is not None:
      self.raw      = self.raw.split("\n\n", 1)
      self.url      = config.site_url+re.sub('-', '/', self.id, 3)
      self.meta     = yaml.load(self.raw[0])
      self.summary  = markdown.markdown(self.raw[1].split('<!-- ~ -->', 1)[0])
      self.body     = markdown.markdown(self.raw[1])
    
  def load(self):
    article = memcache.get(self.id, 'article_')
    if article is None:
      try:
        static_article_path = path(config.articles_dir+self.id+config.article_file_type)
        article = file(static_article_path, 'rb').read()
        memcache.set(self.id, article, config.cache_time, 0, 'article_')
      except IOError: return
    return article

class Articles:
  def all(self):
    archives = Archives().all("", config.articles_per_page)
    articles = []
    for archive in archives:      
      article = Article(archive['name'])
      if article.raw is not None:
        articles.append(article)
    return articles

class Archives:
  def all(self, filter="", limit=25, offset=0):
    index_from  = (limit*offset) 
    index_to    = ((limit*offset)+limit)
    archives = memcache.get('archives_'+filter+"_"+str(index_from)+"_"+str(index_to))
    if archives == None:
      archives    = []
      article_dir = path(config.articles_dir)
      for root, dirs, files in os.walk(article_dir):
        count = 0
        for name in files:
          if filter in name and name.index('.') > 0:
            if count >= index_from and count < index_to:
              name    = re.sub('.md', '', name)
              name    = re.sub('.txt', '', name)
              url     = '/'+re.sub('-', '/', name, 3)
              archive = {
                'name' : name,
                'url'  : url
              }
              archives.append(archive)
            count += 1
      archives = sorted(archives, key=lambda archive:archive['name'])[::-1]
      memcache.set('archives_'+filter+"_"+str(index_from)+"_"+str(index_to), archives, config.cache_time)
    return archives

class Index(webapp.RequestHandler):
  def get(self):
    articles = Articles().all()
    template_vars = { 'articles' : articles }
    self.response.out.write(template.render(path(config.templates_dir+'pages/index.html'), template_vars))

class ViewArticle(webapp.RequestHandler):
  def get(self, year, month, day, title):
    article_id    = cgi.escape(year)+'-'+cgi.escape(month)+'-'+cgi.escape(day)+'-'+cgi.escape(title)
    article       = Article(article_id)
    if article.raw is not None:
      template_vars = { 'article' : article }
      self.response.out.write(template.render(path(config.templates_dir+'pages/article.html'), template_vars))
    else:
      self.response.out.write(template.render(path(config.templates_dir+'pages/404.html'), {}))

class ViewArchives(webapp.RequestHandler):
  def get(self, year=None, month=None, day=None):
    if year == None:
      archives = Archives().all()
    else:
      filter = cgi.escape(year)
      if month is not None: 
        filter += '-'+cgi.escape(month)
        if day is not None: 
          filter += '-'+cgi.escape(day)
      archives = Archives().all(filter)
    template_vars = {
      'year'      : year,
      'month'     : month,
      'day'       : day,
      'archives'  : archives
    }
    self.response.out.write(template.render(path(config.templates_dir+'pages/archives.html'), template_vars))

class PageHandler(webapp.RequestHandler):
  def get(self, page):
    page = cgi.escape(page.replace('/', ''))
    if page == "rss" or page == "sitemap":
      file_type     = ('.xml','.feed')[page == 'rss']
      template_vars = { 
        'title'       : config.site_name,
        'description' : config.site_description,
        'site_url'    : config.site_url,
        'articles'    : Articles().all() 
      }
      self.response.out.write(template.render(path(config.templates_dir+page+file_type), template_vars))
    else:
      try:
        self.response.out.write(template.render(path(config.templates_dir+'pages/'+page+'.html'), {}))
      except TemplateDoesNotExist:
        self.response.out.write(template.render(path(config.templates_dir+'pages/404.html'), {}))

def path(path):
  return os.path.join(os.path.dirname(__file__), path)

class Admin(webapp.RequestHandler):
  def get(self, action):
    if action == "flush":
      self.response.out.write('Flushing...')
      memcache.flush_all()
      self.redirect('/')
    else:
      self.error(404)

def main():
  application = webapp.WSGIApplication(
  [
    ('/', Index),
    ('/(\d{4})/(\d{2})/(\d{2})/([^/]+)/?', ViewArticle),
    ('/archives/?([\d]{4})?/?([\d]{2})?/?([\d]{2})?/?', ViewArchives),
    ('/tag/([^/]+)/?', ViewTag),
    ('/admin/([^/]+)/?', Admin),
    ('/(.*)/?', PageHandler)
  ], 
  debug=True)
  util.run_wsgi_app(application)

if __name__ == '__main__':
  main()