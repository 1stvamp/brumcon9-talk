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

import httplib, re, simplejson, time

from myspace.data import AppData, FriendsAppData
from myspace.oauth import oauth

from xml.dom import minidom

class Consumer (object):
  """
  Client used to communicate with the MySpace apps REST services.

  NOTE: All responses are in the form of dictionaries as parsed from myspace's
  json response.
  """
  SERVER = 'api.myspace.com'
  PORT = 80
  VERSION = 'v1'

  def __init__ (self, key, secret,
      viewer_id=None, server=SERVER, port=PORT, version=VERSION):
    """
    Initializes the client.

    @param key: The oauth consumer key. In MySpace terms, the "Application
    Uri".
    @param secret: The oauth consumer secret. In MySpace terms, the "Security
    Key".
    """
    self.key = key
    self.secret = secret
    self.server = server
    self.port = port
    self.version = version
    self.viewer_id = viewer_id

  def album (self, user_id, album_id):
    return self._request('users/%s/albums/%s/photos' % (user_id, album_id))

  def albums (self, user_id, album_id=None):
    if album_id:
      return self._request('users/%s/albums/%s' % (user_id, album_id))
    return self._request('users/%s/albums' % user_id)

  def appdata (self, keys=None, user_id=None):
    return AppData(self, keys=keys, user_id=user_id)

  def appdataFriends (self, user_id=None, keys=None):
    return FriendsAppData(self, user_id, keys=keys)

  def bulletins (self):
    raise NotImplementedError("not yet implemented")

  def currentUser (self):
    #raise NotImplementedError("not yet implemented")
    if self.viewer_id and self.viewer_id not in (-1, '-1'):
      return self.user(self.viewer_id)
    return None

  def details (self, user_id):
    return self._request('users/%s/details' % user_id)

  def friends (self, user_id, page=None, pageSize=None, listName=None, show=None):
    params = {}
    if page:
      params['page'] = page
    if pageSize:
      params['page_size'] = pageSize
    if listName:
      params['list'] = listName
    if show:
      params['show'] = '|'.join(show)
    return self._request('users/%s/friends' % user_id, params)

  def friendship (self, user_id, user_ids):
    ids = ';'.join([str(uid) for uid in user_ids])
    return self._request('users/%s/friends/%s' % (user_id, ids))

  def groups (self, user_id):
    return self._request('users/%s/groups' % user_id)

  def indicators (self, user_id):
    return self._request('users/%s/indicators' % user_id)

  def interests (self, user_id):
    return self._request('users/%s/interests' % user_id)

  def mood (self, user_id, set_to=None):
    if set_to is not None: # FIXME: I always get 'Method not allowed'
      return self._request(
        'users/%s/mood' % user_id, params={'mood': set_to}, http_method='PUT')
    return self._request('users/%s/mood' % user_id)

  def photo (self, user_id, photo_id):
    return self._request('users/%s/photos/%s' % (user_id, photo_id))

  def photos (self, user_id):
    return self._request('users/%s/photos' % user_id)

  def profile (self, user_id):
    return self._request('users/%s/profile' % user_id)

  def status (self, user_id):
    return self._request('users/%s/status' % user_id)

  # TODO: 'user/' get info about the current user (any different than currentUser?)
  def user (self, user_id):
    return self._request('users/%s' % user_id)

  def video (self, user_id, video_id):
    return self._request('users/%s/videos/%s' % (user_id, video_id))

  def videos (self, user_id):
    return self._request('users/%s/videos' % user_id)

  def _request (self, path, params=None, http_method='GET'):
    consumer = oauth.OAuthConsumer(self.key, self.secret)
    token = oauth.OAuthToken('', '')
    signature_method = oauth.OAuthSignatureMethod_HMAC_SHA1()
    url = 'http://%s/%s/%s.json' % (self.server, self.version, path)
    oauth_request = oauth.OAuthRequest.from_consumer_and_token(
      consumer, token=token, http_method=http_method, http_url=url, parameters=params
    )
    oauth_request.sign_request(signature_method, consumer, None)

    connection = httplib.HTTPConnection('%s:%s' % (self.server, self.port))

    body, headers = None, None
    if http_method in ('POST', 'PUT'):
      body = oauth_request.to_postdata()
      headers = {'Content-Type': 'text/plain'}
      url = oauth_request.to_url()[len('http://%s' % Consumer.SERVER):]
      connection.request(
        oauth_request.http_method,
        url,
        body=body,
        headers=headers,
        #headers=oauth_request.to_header() # this caused invalid signature errors.
      )
    else:
      url = oauth_request.to_url()[len('http://%s' % Consumer.SERVER):]
      connection.request(
        oauth_request.http_method,
        url,
        #headers=oauth_request.to_header() # this caused invalid signature errors.
      )
    response = connection.getresponse()
    if response.status != 200:
      raise MySpaceError(response.status, response.reason, url, response.read())
    json_response = response.read()
    return json_response and simplejson.loads(json_response) or None


class MockConsumer:
  def __init__ (self, secret):
    self.secret = secret


class MySpaceError (Exception):
  """
  Error class used to raise errors reported back by the myspace REST service.
  """

  XML = re.compile(r'^<error\s+xmlns=')

  def __init__ (self, status, reason, url, response):
    self.status = status
    self.reason = reason
    self.url = url
    self.response = response

    # sometimes the response is xml with a more descriptive error message.
    if MySpaceError.XML.search(response):
      try:
        dom = minidom.parseString(self.response)
        self.reason = dom.getElementsByTagName("message")[0].childNodes[0].data
      except:
        pass # don't let an xml error mask the original.

  def __str__ (self):
    return '%s: %s - %s' % (self.status, self.reason, self.url)


def verify_request (key, secret, http_method, http_url, parameters):
  """
  Validates signed requests coming from myspace.
  Returns True if the request is signed and valid. Returns False if the request
  is not signed.  Raises an OAuthError if the request is signed, but invalid.
  """
  if not parameters.has_key('oauth_signature'):
    return False

  oauth_request = oauth.OAuthRequest(http_method, http_url, parameters)
  timestamp, nonce = oauth_request._get_timestamp_nonce()
  _check_timestamp(timestamp)
  signature_method = oauth.OAuthSignatureMethod_HMAC_SHA1()
  signature = oauth_request.get_parameter('oauth_signature')
  built = signature_method.build_signature(
    oauth_request, MockConsumer(secret), oauth.OAuthToken('', ''))

  if signature != built:
    raise oauth.OAuthError('Invalid signature')
  return True


def _check_timestamp (timestamp):
  timestamp_threshold = 1000 * 60 * 15 # 15 minutes
  timestamp = int(timestamp)
  now = int(time.time())
  lapsed = now - timestamp
  if lapsed > timestamp_threshold:
    raise oauth.OAuthError('Expired timestamp: given %d and now %s has a greater difference than threshold %d' % (timestamp, now, timestamp_threshold))
