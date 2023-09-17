class Error(Exception):
  """Generic tfadm error."""
  def __str__(self):
    return ': '.join(self.args)

class Required(Error):
  """Missing configuration key"""
  def __init__(self, context, *args):
    self.context = context
    super().__init__(*args)

  def __str__(self):
    return "{}: Missing configuration property: {}".format(self.context, '/'.join(self.args))

class RequiredArgument(Required):
  """Missing argument"""
  def __str__(self):
    return "{}: Missing argument: {}".format(self.context, '/'.join(self.args))

class PatternError(RequiredArgument):
  def __init__(self, context, *args):
    super().__init__(context, *(*args[:-1], '{' + args[-1] + '}'))
