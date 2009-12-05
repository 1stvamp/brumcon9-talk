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
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseServerError
from django.template import Context, Template

from myspace.app import MySpaceError

def has_app (func):
  """
  Decorator for django views which requires that the user has the app installed.
  Requires that the myspace middleware has been installed and the
  settings.MYSPACE_APP_PROFILE value has been set.
  """
  def _decorator (request, *args, **kwargs):
    # attempt to access the user
    try:
      request.myspace.user
    except MySpaceError, mse:
      if mse.status == 401:
        template = Template(REDIRECT_TEMPLATE, name='Redirect')
        return HttpResponse(template.render(Context({
          'url': settings.MYSPACE_APP_PROFILE,
        })), mimetype='text/html')
      return HttpResponseServerError('%s: %s' % (mse.status, mse.reason));
    return func(request, *args, **kwargs)

  return _decorator


def signed_required (func):
  """
  Decorator for django views which requires that the request is signed.
  Requires that the myspace middleware has been installed.
  """
  def _decorator (request, *args, **kwargs):
    if request.myspace.signed:
      return func(request, *args, **kwargs)
    return HttpResponseForbidden('Signed request required.')

  return _decorator


REDIRECT_TEMPLATE = '''
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
  "http://www.w3.org/TR/html4/loose.dtd">
<html>
  <head>
    <script type="text/javascript">
      window.parent.location = '{{ url }}';
    </script>
  </head>
  <body>
    Attempting to redirect you to:
    <a target="_parent" href="{{ url }}">Application Profile</a>
    <p/>
    If you are not redirected momentarily please click the link above to continue.
  </body>
</html>
'''
