"""
The MIT License

Copyright (c) 2008

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

Author: Eric Van Dewoestine
"""
from django.conf import settings
from django.http import HttpResponseForbidden

from myspace.app import Consumer, verify_request
from myspace.oauth import oauth

class MySpaceMiddleware:
  """
  Middleware which intializes a 'myspace' variable on the current request.
  Requires that you add the following values to your settings.py:
    MYSPACE_KEY = 'application uri'
    MYSPACE_SECRET = 'security key'

  Example: get the current user.
  >>> request.myspace.user

  Example: get another user.
  >>> request.myspace.consumer.user(123456)

  """

  def process_request (self, request):
    params = request.GET.copy()
    url = 'http://%s%s' % (request.META['HTTP_HOST'], request.get_full_path())
    if request.method == 'POST':
      params.update(request.POST)
    try:
      signed = verify_request(
        settings.MYSPACE_KEY, settings.MYSPACE_SECRET, request.method, url, params)
    except oauth.OAuthError, oae:
      return HttpResponseForbidden('OAuthError: %s' % oae.message)

    owner_id = request.GET.get('opensocial_owner_id')
    viewer_id = request.GET.get('opensocial_viewer_id')
    consumer = Consumer(
      settings.MYSPACE_KEY, settings.MYSPACE_SECRET, viewer_id=viewer_id)
    request.myspace = \
        MySpaceMiddleware.MySpace(consumer, owner_id, viewer_id, signed)

  class MySpace:
    def __init__ (self, consumer, owner_id, viewer_id, signed):
      self.consumer = consumer
      self.owner_id = owner_id
      self.viewer_id = viewer_id
      self.signed = signed
      self._user = None

    def _currentUser (self):
      if not self._user:
        self._user = self.consumer.currentUser()
      return self._user
    user = property(_currentUser)
