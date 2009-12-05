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
import simplejson

class AppData:
  """
  Class representing the global, or a user's, stored app data, providing
  support for dictionary like manipulation and retrieval of the data.
  Note: to support values other than strings, numbers, etc., this class will
  store and retrieve non numeric, boolean, or string data in json format.
  However, currently all keys will be retrieved and represented as strings,
  regardless of the data type used to store the key.
  """

  def __init__ (self, consumer, keys=None, user_id=None):
    """
    @param consumer: The myspace consumer used to store and retrieve the data.
    @param keys: Optional list of keys to retrieve.
    @param user_id: When supplied, retrieves and stores data to the given
    user's app data. When omitted, uses the application's global app data.
    """
    self.consumer = consumer
    self.user_id = user_id
    self.keys = keys
    self._data = None

  def __len__ (self):
    self._load()
    return len(self._data)

  def __repr__ (self):
    self._load()
    return repr(self._data)

  def __iter__ (self):
    self._load()
    return iter(self._data)

  def __contains__ (self, k):
    self._load()
    return k in self._data

  def __getitem__ (self, k):
    self._load()
    return self._data[k]

  def __delitem__ (self, k):
    self._load()
    del self._data[k]

  def __setitem__ (self, k, v):
    self._load()
    self._data[k] = v

  def clear (self):
    self._load()
    return self._data.clear()

  def get (self, k, default=None):
    self._load()
    return self._data.get(k, default)

  def has_key (self, k):
    self._load()
    return self._data.has_key(k)

  def items (self):
    self._load()
    return self._data.items()

  def iteritems (self):
    self._load()
    return self._data.iteritems()

  def iterkeys (self):
    self._load()
    return self._data.iterkeys()

  def itervalues (self):
    self._load()
    return self._data.itervalues()

  def keys (self):
    self._load()
    return self._data.keys()

  def update (self, d):
    self._load()
    return self._data.update(d)

  def values (self):
    self._load()
    return self._data.values()

  def save (self):
    """
    Invoke to persist any changes made to this app data.
    """
    if self._data is not None:
      params = {}
      for key, value in self._data.items():
        v = value
        if value is not None and \
           not isinstance(value, basestring) and \
           type(value) not in (bool, int, long, float):
          v = simplejson.dumps(value)
        params[key] = v

      if self.user_id:
        self.consumer._request(
          'users/%s/appdata' % self.user_id, params=params, http_method='PUT')
      else:
        self.consumer._request('appdata/global', params=params, http_method='PUT')

  def _load (self):
    if self._data is None:
      url = self.user_id is not None and \
        'users/%s/appdata' % self.user_id or \
        'appdata/global'

      if self.keys:
        url += '/' + ';'.join(self.keys)

      response = self.consumer._request(url)
      self._data = self._parse(response.get('keyvaluecollection'))

  def _parse (self, collection):
    data = {}
    if collection:
      for pair in collection:
        key = pair.get('key')
        if key and not key.startswith('oauth_'):
          try:
            data[key] = simplejson.loads(pair.get('value'))
          except ValueError, ve: # FIXME: hate using an exception like this
            data[key] = pair.get('value')
    return data


class FriendsAppData:
  """
  Represents a dictionary of app data for all of a user's friends where the key
  is the friend's id and the value is the AppData instance.
  """

  def __init__ (self, consumer, user_id, keys=None):
    """
    @param consumer: The myspace consumer used to store and retrieve the data.
    @param user_id: The id of the user whose friends app data should be
    retrieved for.
    @param keys: Optional list of keys to retrieve.
    """
    self.consumer = consumer
    self.user_id = user_id
    self.keys = keys
    self._data = None

  def __contains__ (self, k):
    self._load()
    return k in self._data

  def __getitem__ (self, k):
    self._load()
    return self._data[k]

  def __len__ (self):
    self._load()
    return len(self._data)

  def __repr__ (self):
    self._load()
    return repr(self._data)

  def __iter__ (self):
    self._load()
    return iter(self._data)

  def get (self, k, default=None):
    self._load()
    return self._data.get(k, default)

  def has_key (self, k):
    self._load()
    return self._data.has_key(k)

  def items (self):
    self._load()
    return self._data.items()

  def iteritems (self):
    self._load()
    return self._data.iteritems()

  def iterkeys (self):
    self._load()
    return self._data.iterkeys()

  def itervalues (self):
    self._load()
    return self._data.itervalues()

  def keys (self):
    self._load()
    return self._data.keys()

  def _load (self):
    if self._data is None:
      url = 'users/%s/friends/appdata' % self.user_id
      if self.keys:
        url += '/' + ';'.join(self.keys)

      response = self.consumer._request(url)
      self._data = {}
      for data in response:
        friend_id = data['userid']
        appdata = AppData(self.consumer, keys=self.keys, user_id=friend_id)
        appdata._data = appdata._parse(data.get('keyvaluecollection'))
        self._data[friend_id] = appdata
