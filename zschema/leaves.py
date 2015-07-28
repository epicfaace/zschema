import unittest
import re
import dateutil.parser

from keys import *

class Leaf(Keyable):

    def __init__(self, required=False, es_index=None, es_analyzer=None, doc=None):
        self.required = required
        self.es_index = es_index
        self.es_analyzer = es_analyzer
        self.doc = doc

    def to_dict(self):
        retv = {
            "required":self.required,
            "doc":self.doc,
            "type":self.__class__.__name__,
            "es_type":self.ES_TYPE,
            "bq_type":self.BQ_TYPE
        }
        self.add_es_var(retv, "es_analyzer", "es_analyzer", "ES_ANALYZER")
        self.add_es_var(retv, "es_index", "es_index", "ES_INDEX")
        return retv

    def to_es(self):
        retv = {"type":self.ES_TYPE}
        self.add_es_var(retv, "index", "es_index", "ES_INDEX")
        if "index" in retv:
            assert retv["index"] in self.VALID_ES_INDEXES
        self.add_es_var(retv, "analyzer", "es_analyzer", "ES_ANALYZER")
        if "analyzer" in retv:
            assert retv["analyzer"] in self.VALID_ES_ANALYZERS
        return retv
        
    def to_bigquery(self, name):
        mode = "REQUIRED" if self.required else "NULLABLE"
        retv = {"name":self.key_to_bq(name), "type":self.BQ_TYPE, "mode":mode}
        if self.doc:
            retv["doc"] = self.doc
        return retv

    def to_string(self, name):
        return "%s: %s" % (self.key_to_string(name), 
                           self.__class__.__name__.lower())
                           
    def to_flat(self, parent, name):
        full_name = ".".join([parent, name])
        return {
            "name":full_name,
            "type":self.__class__.__name__,
            "documentation":self.doc,
            "mode":"required" if self.required else "optional"
        }
        
    def print_indent_string(self, name, indent):
        val = self.key_to_string(name)
        if indent:
            tabs = "\t" * indent
            val = tabs + val
        print val
        
    def validate(self, name, value):
        if value is None:
            if self.required:
                raise DataValidationException("%s is a required field, but "
                                              "recieved None" % name)
            else:
                return
        if type(value) not in self.EXPECTED_CLASS:
            m = "class mismatch for %s: expected %s, %s has class %s" % (\
                    self.key_to_string(name), self.EXPECTED_CLASS, 
                    str(value), value.__class__.__name__)
            raise DataValidationException(m)
        if hasattr(self, "_validate"):
            self._validate(str(name), value)



class EnglishString(Leaf):
    ES_TYPE = "string"
    BQ_TYPE = "STRING"
    ES_INDEX = "analyzed"
    ES_ANALYZER = "standard"
    EXPECTED_CLASS = [str,unicode]
    
    INVALID = 23
    VALID = "asdf"


class AnalyzedString(Leaf):
    ES_TYPE = "string"
    BQ_TYPE = "STRING"
    ES_INDEX = "analyzed"
    ES_ANALYZER = "simple"
    EXPECTED_CLASS = [str,unicode]
    
    INVALID = 23
    VALID = "asdf"


class String(Leaf):
    ES_TYPE = "string"
    BQ_TYPE = "STRING"
    ES_INDEX = "not_analyzed"
    EXPECTED_CLASS = [str,unicode]

    INVALID = 23
    VALID = "asdf"


class IPv4Address(Leaf):
    ES_TYPE = "ip"
    BQ_TYPE = "STRING"
    EXPECTED_CLASS = [str,unicode]
    IP_REGEX = re.compile('(\d{1,3}\.){3}\d{1,3}')
    
    def _is_ipv4_addr(self, ip):
        return bool(self.IP_REGEX.match(ip))
    
    def _validate(self, name, value):
        if not self._is_ipv4_addr(value):
            m = "%s: the value %s is not a valid IPv4 address" % (name, value)
            raise DataValidationException(m)
        
    INVALID = "my string"
    VALID = "141.212.120.0"


class Integer(Leaf):
    ES_TYPE = "integer"
    BQ_TYPE = "INTEGER"
    EXPECTED_CLASS = [int,]
    
    INVALID = 8589934592
    VALID = 234234252
    
    BITS = 32

    def _validate(self, name, value):
        max_ = 2**self.BITS - 1
        min_ = -2**self.BITS + 1
        if value > max_:
            raise DataValidationException("%s: %s is larger than max (%s)" % (\
                    name, str(value), str(max_)))
        if value < min_:
            raise DataValidationException("%s: %s is smaller than min (%s)" % (\
                    name, str(value), str(min_)))


class Byte(Integer):
    ES_TYPE = "byte"
    BITS = 8
    INVALID = 2**8+5
    VALID = 34


class Short(Integer):
    ES_TYPE = "short"
    BITS = 16
    INVALID = 2**16
    VALID = 0xFFFF


class Long(Integer):
    ES_TYPE = "long"
    BQ_TYPE = "DOUBLE"
    EXPECTED_CLASS = [int,long]
    INVALID = 2l**68
    VALID = 10l
    BITS = 64
    

class Float(Leaf):
    ES_TYPE = "float"
    BQ_TYPE = "FLOAT"
    EXPECTED_CLASS = [float,]
    INVALID = "I'm a string!"
    VALID = 10.0
    

class Double(Float):
    ES_TYPE = "double"
    BQ_TYPE = "FLOAT"
    EXPECTED_CLASS = [float,]


class Boolean(Leaf):
    ES_TYPE = "boolean"
    BQ_TYPE = "BOOLEAN"
    EXPECTED_CLASS = [bool,]
    INVALID = 0
    VALID = True


class Binary(Leaf):
    ES_TYPE = "binary"
    BQ_TYPE = "STRING"
    ES_INDEX = "no"
    EXPECTED_CLASS = [str,unicode]
    B64_REGEX = re.compile('^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$')
    
    def _is_base64(self, data):
        return bool(self.B64_REGEX.match(data))
    
    def _validate(self, name, value):
        if not self._is_base64(value):
            m = "%s: the value %s is not valid Base64" % (name, value)
            raise DataValidationException(m)

    VALID = "03F87824"
    INVALID = "normal"
    

class IndexedBinary(Binary):
    ES_TYPE = "binary"
    BQ_TYPE = "STRING"
    ES_INDEX = "not_analyzed"


class DateTime(Leaf):
    ES_TYPE = "datetime"
    BQ_TYPE = "TIMESTAMP"
    EXPECTED_CLASS = [str, int, unicode]
    
    VALID = "Wed Jul  8 08:52:01 EDT 2015"
    INVALID = "Wed DNE  35 08:52:01 EDT 2015"
    
    def _validate(self, name, value):
        try:
            dateutil.parser.parse(value)
        except Exception, e:
            m = "%s: %s is not valid timestamp" % (name, str(value))
            raise DataValidationException(m)


VALID_LEAVES = [
    DateTime,
    AnalyzedString,
    String,
    Binary,
    IndexedBinary,
    Boolean,
    Double,
    Float,
    Long,
    Short,
    Byte,
    Integer,
    IPv4Address
]

