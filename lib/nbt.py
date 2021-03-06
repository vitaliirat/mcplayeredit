
# vim:set sw=2 sts=2 ts=2:

"""

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

DO NOT USE THIS LIBRARY, IT HAS BEEN MODIFIED FOR SPECIAL PURPOSES AND MAY
CORRUPT YOUR SAVE FILES!!  GET THE OFFICIAL VERSION FROM
http://github.com/codewarrior0/pymclevel

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

Named Binary Tag library. Serializes and deserializes TAG_* objects
to and from binary data. Load a Minecraft level by calling nbt.load().
Create your own TAG_* objects and set their values.  
Save a TAG_* object to a file or StringIO object.

Read the test functions at the end of the file to get started.

Official NBT documentation is here:
http://www.minecraft.net/docs/NBT.txt


Copyright 2010 David Rio Vierra

Modified to not need Numpy.
"""
import collections
import itertools
import struct
import gzip
import StringIO;
from array import array
####from numpy import array, zeros, uint8, fromstring
#from numpy import uint8
TAGfmt = ">b"

class TAG_Value(object):
  """Simple values. Subclasses override fmt to change the type and size. 
  Subclasses may set dataType instead of overriding setValue for automatic data type coercion"""
  
  fmt = ">b";
  tag = -1; #error!
  
  _value = None
  def getValue(self):
      return self._value
  def setValue(self, newVal):
      self._value = self.dataType(newVal)
  value = property(getValue, setValue, None, "Change the TAG's value.  Data types are checked and coerced if needed.")
  
  _name = None
  def getName(self):
      return self._name
  def setName(self, newVal):
      self._name = str(newVal)
  def delName(self):
      self._name = ""
  name = property(getName, setName, delName, "Change the TAG's name.  Coerced to a string.")
      
  def __init__(self, value=0, name=None, data=""):
    self.name=name
    if(data==""):
        self.value = value
    else:   
        (self.value,) = struct.unpack_from(self.fmt, data);
  
  def __repr__(self):
    return "%s ( %s ) : %s" % (self.__class__, self.name, repr(self.value))
  def nbt_length(self):
    return struct.calcsize(self.fmt);
  
  def write_tag(self, buf):
    buf.write(struct.pack(TAGfmt, self.tag))
  def write_name(self, buf):
    if(self.name!=None):
      TAG_String(self.name).write_value(buf)
  def write_value(self, buf):
    buf.write(struct.pack(self.fmt, self.value))
    
  def save(self, filename = "", buf = None):
    if(filename):
      self.saveGzipped(filename);
      return;
    "Save the tagged element to a file."
    if self.name == None: self.name = "" #root tag must have name
    self.write_tag(buf)
    self.write_name(buf)
    self.write_value(buf)

  def saveGzipped(self, filename, compresslevel=1):
    sio = StringIO.StringIO();
    #atomic write
    try: os.rename(filename, filename + ".old");
    except Exception,e:
      #print "Atomic Save: No existing file to rename"
      pass
  
    outputGz = gzip.GzipFile(fileobj=sio, mode="wb", compresslevel=compresslevel)
    self.save(buf=outputGz);
    outputGz.flush();
    outputGz.close();
    #print len(sio.getvalue());
    try:
      file(filename, "wb").write(sio.getvalue());
    except:
      try:
        os.rename(filename + ".old", filename, );
      except Exception, e:
        print e;
        return
      
    try: os.remove(filename + ".old");
    except Exception,e:
      #print "Atomic Save: No old file to remove"
      pass;
  
class TAG_Byte(TAG_Value):
  tag = 1;
  fmt = ">b";
  dataType = int
    
class TAG_Short(TAG_Value):
  tag = 2;
  fmt = ">h";
  dataType = int
    
class TAG_Int(TAG_Value):
  tag = 3;
  fmt = ">i";
  dataType = int
    
class TAG_Long(TAG_Value):
  tag = 4;
  fmt = ">q";
  dataType = long

class TAG_Float(TAG_Value):
  tag = 5;
  fmt = ">f";
  dataType = float

    
class TAG_Double(TAG_Value):
  tag = 6;
  fmt = ">d";
  dataType = float


class TAG_Byte_Array(TAG_Value):
  """Like a string, but for binary data.  four length bytes instead of
  two.  value is a numpy array, and you can change its elements"""

  tag = 7;
  fmt = ">i%ds"

  def dataType(self, value):
      ####return array(value, uint8)
      return array('B', value)
      
  def __repr__(self):
    return "<%s: length %d> ( %s )" % (self.__class__, len(self.value), self.name)
  
  #####def __init__(self, value=zeros(0, uint8), name=None, data=""):
  def __init__(self, value=array('B'), name=None, data=""):
    self.name=name
    if(data==""):
      self.value = value;
    else:
      (string_len,) = struct.unpack_from(">i", data);
      ####self.value = fromstring(data[4:string_len+4], 'uint8');
      self.value = data[4:string_len+4]
      
  def nbt_length(self) :
    return len(self.value) + 4;
       
  def write_value(self, buf):
    #print self.value
    valuestr = self.value.tostring()
    buf.write(struct.pack(self.fmt % (len(valuestr),), len(valuestr), valuestr))
   

class TAG_String(TAG_Value):
  "String in UTF-8"

  tag = 8;
  fmt = ">h%ds"
  dataType = str
  
  def __init__(self, value="", name=None, data=""):
    self.name=name
    if(data==""):
      self.value = value;
    else:
      (string_len,) = struct.unpack_from(">h", data);
      self.value = data[2:string_len+2].tostring();

  def nbt_length(self) :
    return len(self.value) + 2;

  def write_value(self, buf):
    buf.write(struct.pack(self.fmt % (len(self.value),), len(self.value), self.value))
    



class TAG_Compound(TAG_Value, collections.MutableMapping):
  """A heterogenous list of named tags. Names must be unique within
  the TAG_Compound. Add tags to the compound using the subscript
  operator [].  This will automatically name the tags."""

  tag = 10;
  
  def dataType(self, val):
      for i in val:
          assert isinstance(i, TAG_Value)
          assert i.name
      return list(val)
  
  def __repr__(self):
    return "%s( %s ): %s" % (str(self.__class__), self.name, self.value)

  def __init__(self, value=[], name="",data=""):
      
    self.name=name;
    if value.__class__ == ''.__class__:
      self.name = value;
      value = [];
    self.value = []
    if(data == ""):
      self.value += value;
    else:

      data_cursor = 0;
      
      while data_cursor < len(data):
        tag_type = data[data_cursor];
        data_cursor += 1;
        if(tag_type == 0):
          break;

        assert_type(tag_type, data_cursor)
        
        
        data_cursor, tag = load_named(data, data_cursor, tag_type)
        
        self.value.append(tag);
        
      
  def nbt_length(self):
    return sum(x.nbt_length() + len(x.name) + 3 for x in self.value) + 1;
  
  def write_value(self, buf):
    for i in self.value:
      i.save(buf=buf)
    buf.write("\x00")
    
  "collection functions"
  def __getitem__(self, k):
    #hits=filter(lambda x:x.name==k, self.value);
    #if(len(hits)): return hits[0];
    for key in self.value:
        if key.name == k: return key
    raise KeyError("Key {0} not found".format(k));
  
  def __iter__(self):       return itertools.imap(lambda x:x.name, self.value);
  def __contains__(self, k):return k in map(lambda x:x.name, self.value);
  def __len__(self):        return self.value.__len__()
  

  def __setitem__(self, k, v):
    if not (v.__class__ in tag_handlers.values()): raise TypeError("Invalid type %s for TAG_Compound" % (v.__class__))
    """remove any items already named "k".  """
    olditems = filter(lambda x:x.name==k, self.value)
    for i in olditems: self.value.remove(i)
    self.value.append(v);
    v.name=k;
    
  def __delitem__(self, k): self.value.__delitem__(self.value.index(self[k]));

  def add(self, v):
    self[v.name] = v;
    
class TAG_List(TAG_Value, collections.MutableSequence):
  
  """A homogenous list of unnamed data of a single TAG_* type. 
  Once created, the type can only be changed by emptying the list 
  and adding an element of the new type. If created with no arguments,
  returns a list of TAG_Compound
  
  Empty lists in the wild have been seen with type TAG_Byte"""

  tag = 9;
  
  def setValue(self, val):
      listType = TAG_Value
      for i in val:
          assert isinstance(val, listType)
          assert val.name == ""
          listType = val.__class__
      list = list(val)
  
  def __repr__(self):
    return "%s( %s ): %s" % (self.__class__, self.name, self.list)

  def __init__(self, value=[], name=None, data=None, list_type=TAG_Compound):
    #can be created from a list of tags in value, with an optional
    #name, or created from raw tag data, or created with list_type
    #taken from a TAG class or instance
    
    self.name=name
    self.list = [];
    self.list_type = list_type.tag
    
    if(data == None):
      if(len(value)):
        self.list_type = value[0].tag;
        value = filter(lambda x:x.__class__ == value[0].__class__, value)
        
      self.list = list(value)

    else: 
      data_cursor = 0;

      self.list_type = data[data_cursor];
      assert_type(self.list_type, data_cursor);
      
      data_cursor += 1;

      list_length = TAG_Int( data=data[data_cursor:] )
      data_cursor += list_length.nbt_length()
      list_length = list_length.value

      
      for i in range(list_length):
        
        tag = tag_handlers[self.list_type]( data=data[data_cursor:])
        self.append(tag);
        data_cursor += tag.nbt_length()

  """ collection methods """
  def __iter__(self):       return self.list.__iter__();
  def __contains__(self, k):return k in self.list;
  def __getitem__(self, i): return self.list[i];
  def __len__(self):        return self.list.__len__()
  
  def __setitem__(self, i, v):
    if v.__class__ != tag_handlers[self.list_type]: raise TypeError("Invalid type %s for TAG_List(%s)" % (v.__class__, tag_handlers[self.list_type]))
    v.name = ""
    self.list[i] = v;
    
  def __delitem__(self, i): self.list.__delitem__(i);
  
  def insert(self, i, v):
      if not v.tag in tag_handlers: raise TypeError("Not a tag type: %s" % (v,))
      if len(self.list) == 0: 
          self.list_type = v.tag 
      else:
          if v.__class__ != tag_handlers[self.list_type]: raise TypeError("Invalid type %s for TAG_List(%s)" % (v.__class__, tag_handlers[self.list_type]))
    
      v.name = ""
      self.list.insert(i, v);
  
  def nbt_length(self):
    return 5 + sum(x.nbt_length() for x in self.list)
  
  def write_value(self, buf):
    buf.write(struct.pack(TAGfmt, self.list_type))
    TAG_Int(len(self.list)).write_value(buf)
    for i in self.list:
      i.write_value(buf)
 

                    
tag_handlers = {
    1 : TAG_Byte,
    2 : TAG_Short,
    3 : TAG_Int,
    4 : TAG_Long,
    5 : TAG_Float,
    6 : TAG_Double,
    7 : TAG_Byte_Array,
    8 : TAG_String,
    9 : TAG_List,
    10: TAG_Compound
    };

def assert_type(t, offset) :
  if not t in tag_handlers: raise TypeError("Unexpected type %d at %d" % (t, offset));

def loadFile(filename):
    #sio = StringIO.StringIO();
    inputGz = gzip.GzipFile(filename, mode="rb")
    try:
      data = inputGz.read();
    except IOError:
      print "File %s not zipped" % filename
      data = file(filename, "rb").read();
    else:
      ####return load(buf=fromstring(data, 'uint8'));
      return load(buf=data);

def load_named(data, data_cursor, tag_type):
    tag_name = TAG_String( data=data[data_cursor:] )
    data_cursor += tag_name.nbt_length()
    tag_name = tag_name.value
    
    tag = tag_handlers[tag_type]( data=data[data_cursor:], name=tag_name)
    data_cursor += tag.nbt_length()
    return data_cursor, tag

def load(filename="", buf = None):
    """Unserialize data from an entire NBT file and return the 
    root TAG_Compound object. Argument can be a string containing a 
    filename or an array of integers containing TAG_Compound data. """
    
    if filename and isinstance(filename, str):
      return loadFile(filename)
    ####if isinstance(buf, str): buf = fromstring(buf, uint8)
    if isinstance(buf, str): buf = array('B', buf)
    data = buf;
    #if buf != None: data = buf
    if not len(buf):
        raise IOError, "Asked to load root tag of zero length"

    data_cursor = 0;
    tag_type = data[data_cursor];
    if tag_type != 10:
      raise IOError, 'Not an NBT file with a root TAG_Compound (found {0})'.format(tag_type);
    data_cursor += 1;

    data_cursor, tag = load_named(data, data_cursor, tag_type)

    return tag;



def loadtest():
    "Load an indev level."
    level = load("hell.mclevel");

    """The root tag must have a name, and so must any tag within a TAG_Compound"""
    print level.name

    """Use the [] operator to look up subtags of a TAG_Compound."""
    print level["Environment"]["SurroundingGroundHeight"].value;
    
    
    """Numeric, string, and bytearray types have a value 
    that can be accessed and changed. """
    print level["Map"]["Blocks"].value
    
    return level;
