# This file was automatically generated by SWIG (http://www.swig.org).
# Version 1.3.40
#
# Do not make changes to this file unless you know what you are doing--modify
# the SWIG interface file instead.

from sys import version_info
if version_info >= (3,0,0):
    new_instancemethod = lambda func, inst, cls: _x86_64_exec.SWIG_PyInstanceMethod_New(func)
else:
    from new import instancemethod as new_instancemethod
if version_info >= (2,6,0):
    def swig_import_helper():
        from os.path import dirname
        import imp
        fp = None
        try:
            fp, pathname, description = imp.find_module('_x86_64_exec', [dirname(__file__)])
        except ImportError:
            import _x86_64_exec
            return _x86_64_exec
        if fp is not None:
            try:
                _mod = imp.load_module('_x86_64_exec', fp, pathname, description)
            finally:
                fp.close()
            return _mod
    _x86_64_exec = swig_import_helper()
    del swig_import_helper
else:
    import _x86_64_exec
del version_info
try:
    _swig_property = property
except NameError:
    pass # Python < 2.2 doesn't have 'property'.
def _swig_setattr_nondynamic(self,class_type,name,value,static=1):
    if (name == "thisown"): return self.this.own(value)
    if (name == "this"):
        if type(value).__name__ == 'SwigPyObject':
            self.__dict__[name] = value
            return
    method = class_type.__swig_setmethods__.get(name,None)
    if method: return method(self,value)
    if (not static) or hasattr(self,name):
        self.__dict__[name] = value
    else:
        raise AttributeError("You cannot add attributes to %s" % self)

def _swig_setattr(self,class_type,name,value):
    return _swig_setattr_nondynamic(self,class_type,name,value,0)

def _swig_getattr(self,class_type,name):
    if (name == "thisown"): return self.this.own()
    method = class_type.__swig_getmethods__.get(name,None)
    if method: return method(self)
    raise AttributeError(name)

def _swig_repr(self):
    try: strthis = "proxy of " + self.this.__repr__()
    except: strthis = ""
    return "<%s.%s; %s >" % (self.__class__.__module__, self.__class__.__name__, strthis,)

try:
    _object = object
    _newclass = 1
except AttributeError:
    class _object : pass
    _newclass = 0


def _swig_setattr_nondynamic_method(set):
    def set_attr(self,name,value):
        if (name == "thisown"): return self.this.own(value)
        if hasattr(self,name) or (name == "this"):
            set(self,name,value)
        else:
            raise AttributeError("You cannot add attributes to %s" % self)
    return set_attr


class ExecParams(object):
    thisown = _swig_property(lambda x: x.this.own(), lambda x, v: x.this.own(v), doc='The membership flag')
    __repr__ = _swig_repr
    p1 = _swig_property(_x86_64_exec.ExecParams_p1_get, _x86_64_exec.ExecParams_p1_set)
    p2 = _swig_property(_x86_64_exec.ExecParams_p2_get, _x86_64_exec.ExecParams_p2_set)
    p3 = _swig_property(_x86_64_exec.ExecParams_p3_get, _x86_64_exec.ExecParams_p3_set)
    p4 = _swig_property(_x86_64_exec.ExecParams_p4_get, _x86_64_exec.ExecParams_p4_set)
    p5 = _swig_property(_x86_64_exec.ExecParams_p5_get, _x86_64_exec.ExecParams_p5_set)
    p6 = _swig_property(_x86_64_exec.ExecParams_p6_get, _x86_64_exec.ExecParams_p6_set)
    def __init__(self): 
        _x86_64_exec.ExecParams_swiginit(self,_x86_64_exec.new_ExecParams())
    __swig_destroy__ = _x86_64_exec.delete_ExecParams
ExecParams_swigregister = _x86_64_exec.ExecParams_swigregister
ExecParams_swigregister(ExecParams)

class ThreadParams(object):
    thisown = _swig_property(lambda x: x.this.own(), lambda x, v: x.this.own(v), doc='The membership flag')
    __repr__ = _swig_repr
    addr = _swig_property(_x86_64_exec.ThreadParams_addr_get, _x86_64_exec.ThreadParams_addr_set)
    params = _swig_property(_x86_64_exec.ThreadParams_params_get, _x86_64_exec.ThreadParams_params_set)
    ret = _swig_property(_x86_64_exec.ThreadParams_ret_get)
    def __init__(self): 
        _x86_64_exec.ThreadParams_swiginit(self,_x86_64_exec.new_ThreadParams())
    __swig_destroy__ = _x86_64_exec.delete_ThreadParams
ThreadParams_swigregister = _x86_64_exec.ThreadParams_swigregister
ThreadParams_swigregister(ThreadParams)

class ThreadParams_ret(object):
    thisown = _swig_property(lambda x: x.this.own(), lambda x, v: x.this.own(v), doc='The membership flag')
    __repr__ = _swig_repr
    l = _swig_property(_x86_64_exec.ThreadParams_ret_l_get, _x86_64_exec.ThreadParams_ret_l_set)
    d = _swig_property(_x86_64_exec.ThreadParams_ret_d_get, _x86_64_exec.ThreadParams_ret_d_set)
    def __init__(self): 
        _x86_64_exec.ThreadParams_ret_swiginit(self,_x86_64_exec.new_ThreadParams_ret())
    __swig_destroy__ = _x86_64_exec.delete_ThreadParams_ret
ThreadParams_ret_swigregister = _x86_64_exec.ThreadParams_ret_swigregister
ThreadParams_ret_swigregister(ThreadParams_ret)

class ThreadInfo(object):
    thisown = _swig_property(lambda x: x.this.own(), lambda x, v: x.this.own(v), doc='The membership flag')
    __repr__ = _swig_repr
    th = _swig_property(_x86_64_exec.ThreadInfo_th_get, _x86_64_exec.ThreadInfo_th_set)
    mode = _swig_property(_x86_64_exec.ThreadInfo_mode_get, _x86_64_exec.ThreadInfo_mode_set)
    def __init__(self): 
        _x86_64_exec.ThreadInfo_swiginit(self,_x86_64_exec.new_ThreadInfo())
    __swig_destroy__ = _x86_64_exec.delete_ThreadInfo
ThreadInfo_swigregister = _x86_64_exec.ThreadInfo_swigregister
ThreadInfo_swigregister(ThreadInfo)


def make_executable(*args):
  return _x86_64_exec.make_executable(*args)
make_executable = _x86_64_exec.make_executable

def cancel_async(*args):
  return _x86_64_exec.cancel_async(*args)
cancel_async = _x86_64_exec.cancel_async

def suspend_async(*args):
  return _x86_64_exec.suspend_async(*args)
suspend_async = _x86_64_exec.suspend_async

def resume_async(*args):
  return _x86_64_exec.resume_async(*args)
resume_async = _x86_64_exec.resume_async

def cleanup(*args):
  return _x86_64_exec.cleanup(*args)
cleanup = _x86_64_exec.cleanup

def run_stream_int(*args):
  return _x86_64_exec.run_stream_int(*args)
run_stream_int = _x86_64_exec.run_stream_int

def run_stream_fp(*args):
  return _x86_64_exec.run_stream_fp(*args)
run_stream_fp = _x86_64_exec.run_stream_fp

def execute_int_async(*args):
  return _x86_64_exec.execute_int_async(*args)
execute_int_async = _x86_64_exec.execute_int_async

def execute_fp_async(*args):
  return _x86_64_exec.execute_fp_async(*args)
execute_fp_async = _x86_64_exec.execute_fp_async

def join_int(*args):
  return _x86_64_exec.join_int(*args)
join_int = _x86_64_exec.join_int

def join_fp(*args):
  return _x86_64_exec.join_fp(*args)
join_fp = _x86_64_exec.join_fp

def execute_int(*args):
  return _x86_64_exec.execute_int(*args)
execute_int = _x86_64_exec.execute_int

def execute_fp(*args):
  return _x86_64_exec.execute_fp(*args)
execute_fp = _x86_64_exec.execute_fp

