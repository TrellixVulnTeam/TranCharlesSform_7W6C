# coding=utf-8
# Copyright 2018 The Tensor2Tensor Authors.
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
"""Registry for models, hyperparameter settings, problem types, and datasets.

Define a new model by subclassing T2TModel and register it:

```
@registry.register_model
class MyModel(T2TModel):
  ...
```

Access by snake-cased name: `registry.model("my_model")`. If you're using
`t2t_trainer.py`, you can pass on the command-line: `--model=my_model`.

See all the models registered: `registry.list_models()`.

For hyperparameter sets:
  * Register: `registry.register_hparams`
  * List: `registry.list_hparams`
  * Retrieve by name: `registry.hparams`
  * Command-line flag in `t2t_trainer.py`: `--hparams_set=name`

For hyperparameter ranges:
  * Register: `registry.register_ranged_hparams`
  * List: `registry.list_ranged_hparams`
  * Retrieve by name: `registry.ranged_hparams`
  * Command-line flag in `t2t_trainer.py`: `--hparams_range=name`
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import inspect
import re
import six
import tensorflow as tf

_MODELS = {}
_HPARAMS = {}
_RANGED_HPARAMS = {}
_ATTACKS = {}
_ATTACK_PARAMS = {}
_PROBLEMS = {}


class Modalities(object):
  SYMBOL = "symbol"
  IMAGE = "image"
  AUDIO = "audio"
  VIDEO = "video"
  CLASS_LABEL = "class_label"
  GENERIC = "generic"
  REAL = "real"


_MODALITIES = {
    Modalities.SYMBOL: {},
    Modalities.IMAGE: {},
    Modalities.AUDIO: {},
    Modalities.VIDEO: {},
    Modalities.CLASS_LABEL: {},
    Modalities.GENERIC: {},
    Modalities.REAL: {},
}

# Camel case to snake case utils
_first_cap_re = re.compile("(.)([A-Z][a-z0-9]+)")
_all_cap_re = re.compile("([a-z0-9])([A-Z])")


def _convert_camel_to_snake(name):
  s1 = _first_cap_re.sub(r"\1_\2", name)
  return _all_cap_re.sub(r"\1_\2", s1).lower()


def _reset():
  for ctr in [_MODELS, _HPARAMS, _RANGED_HPARAMS, _ATTACK_PARAMS] + list(
      _MODALITIES.values()):
    ctr.clear()


def default_name(obj_class):
  """Convert a class name to the registry's default name for the class.

  Args:
    obj_class: the name of a class

  Returns:
    The registry's default name for the class.
  """
  return _convert_camel_to_snake(obj_class.__name__)


def default_object_name(obj):
  """Convert an object to the registry's default name for the object class.

  Args:
    obj: an object instance

  Returns:
    The registry's default name for the class of the object.
  """
  return default_name(obj.__class__)


def register_model(name=None):
  """Register a model. name defaults to class name snake-cased."""

  def decorator(model_cls, registration_name=None):
    """Registers & returns model_cls with registration_name or default name."""
    model_name = registration_name or default_name(model_cls)
    if model_name in _MODELS and not tf.contrib.eager.in_eager_mode():
      raise LookupError("Model %s already registered." % model_name)
    model_cls.REGISTERED_NAME = model_name
    _MODELS[model_name] = model_cls
    return model_cls

  # Handle if decorator was used without parens
  if callable(name):
    model_cls = name
    return decorator(model_cls, registration_name=default_name(model_cls))

  return lambda model_cls: decorator(model_cls, name)

# MAIN STEP Build Model 
def model(name):
  if name not in _MODELS:
    raise LookupError("Model %s never registered.  Available models:\n %s" %
                      (name, "\n".join(list_models())))

  return _MODELS[name]


def list_models():
  return list(sorted(_MODELS))


def register_hparams(name=None):
  """Register an HParams set. name defaults to function name snake-cased."""

  def decorator(hp_fn, registration_name=None):
    """Registers & returns hp_fn with registration_name or default name."""
    hp_name = registration_name or default_name(hp_fn)
    if hp_name in _HPARAMS and not tf.contrib.eager.in_eager_mode():
      raise LookupError("HParams set %s already registered." % hp_name)
    _HPARAMS[hp_name] = hp_fn
    return hp_fn

  # Handle if decorator was used without parens
  if callable(name):
    hp_fn = name
    return decorator(hp_fn, registration_name=default_name(hp_fn))

  return lambda hp_fn: decorator(hp_fn, name)


def hparams(name):
  """Retrieve registered hparams by name."""
  if name not in _HPARAMS:
    error_msg = "HParams set %s never registered. Sets registered:\n%s"
    raise LookupError(
        error_msg % (name,
                     display_list_by_prefix(list_hparams(), starting_spaces=4)))
  hp = _HPARAMS[name]()
  if hp is None:
    raise TypeError("HParams %s is None. Make sure the registered function "
                    "returns the HParams object." % name)
  return hp


def list_hparams(prefix=None):
  if prefix:
    return [name for name in _HPARAMS if name.startswith(prefix)]
  return list(_HPARAMS)


def register_ranged_hparams(name=None):
  """Register a RangedHParams set. name defaults to fn name snake-cased."""

  def decorator(rhp_fn, registration_name=None):
    """Registers & returns hp_fn with registration_name or default name."""
    rhp_name = registration_name or default_name(rhp_fn)
    if rhp_name in _RANGED_HPARAMS:
      raise LookupError("RangedHParams set %s already registered." % rhp_name)
    # Check that the fn takes a single argument
    args, varargs, keywords, _ = inspect.getargspec(rhp_fn)
    if len(args) != 1 or varargs is not None or keywords is not None:
      raise ValueError("RangedHParams set function must take a single "
                       "argument, the RangedHParams object.")

    _RANGED_HPARAMS[rhp_name] = rhp_fn
    return rhp_fn

  # Handle if decorator was used without parens
  if callable(name):
    rhp_fn = name
    return decorator(rhp_fn, registration_name=default_name(rhp_fn))

  return lambda rhp_fn: decorator(rhp_fn, name)


def ranged_hparams(name):
  if name not in _RANGED_HPARAMS:
    raise LookupError("RangedHParams set %s never registered." % name)
  return _RANGED_HPARAMS[name]


def list_ranged_hparams():
  return list(_RANGED_HPARAMS)


def register_problem(name=None):
  """Register a Problem. name defaults to cls name snake-cased."""

  def decorator(p_cls, registration_name=None):
    """Registers & returns p_cls with registration_name or default name."""
    p_name = registration_name or default_name(p_cls)
    if p_name in _PROBLEMS and not tf.contrib.eager.in_eager_mode():
      raise LookupError("Problem %s already registered." % p_name)

    _PROBLEMS[p_name] = p_cls
    p_cls.name = p_name
    return p_cls

  # Handle if decorator was used without parens
  if callable(name):
    p_cls = name
    return decorator(p_cls, registration_name=default_name(p_cls))

  return lambda p_cls: decorator(p_cls, name)


def problem(name):
  """Retrieve a problem by name."""

  def parse_problem_name(problem_name):
    """Determines if problem_name specifies a copy and/or reversal.

    Args:
      problem_name: str, problem name, possibly with suffixes.

    Returns:
      base_name: A string with the base problem name.
      was_reversed: A boolean.
      was_copy: A boolean.
    """
    # Recursively strip tags until we reach a base name.
    if problem_name.endswith("_rev"):
      base, _, was_copy = parse_problem_name(problem_name[:-4])
      return base, True, was_copy
    elif problem_name.endswith("_copy"):
      base, was_reversed, _ = parse_problem_name(problem_name[:-5])
      return base, was_reversed, True
    else:
      return problem_name, False, False

  base_name, was_reversed, was_copy = parse_problem_name(name)

  if base_name not in _PROBLEMS:
    all_problem_names = list_problems()
    error_lines = ["%s not in the set of supported problems:" % base_name
                  ] + all_problem_names
    error_msg = "\n  * ".join(error_lines)
    raise LookupError(error_msg)
  return _PROBLEMS[base_name](was_reversed, was_copy)


def list_problems():
  return sorted(list(_PROBLEMS))


def register_attack(name=None):
  """Register an attack HParams set. Same behaviour as register_hparams."""

  def decorator(attack_fn, registration_name=None):
    """Registers & returns attack_fn with registration_name or default name."""
    attack_name = registration_name or default_name(attack_fn)
    if attack_name in _ATTACKS and not tf.contrib.eager.in_eager_mode():
      raise LookupError("Attack %s already registered." % attack_name)
    _ATTACKS[attack_name] = attack_fn
    return attack_fn

  # Handle if decorator was used without parens
  if callable(name):
    attack_fn = name
    return decorator(attack_fn, registration_name=default_name(attack_fn))

  return lambda attack_fn: decorator(attack_fn, name)


def attacks(name):
  """Retrieve registered attack by name."""
  if name not in _ATTACKS:
    error_msg = "Attack %s never registered. Sets registered:\n%s"
    raise LookupError(
        error_msg % (name,
                     display_list_by_prefix(list_attacks(), starting_spaces=4)))
  attack = _ATTACKS[name]()
  if attack is None:
    raise TypeError(
        "Attack %s is None. Make sure the registered function returns a "
        "`cleverhans.attack.Attack` object." % name)
  return attack


def list_attacks(prefix=None):
  if prefix:
    return [name for name in _ATTACKS if name.startswith(prefix)]
  return list(_ATTACKS)


def register_attack_params(name=None):
  """Register an attack HParams set. Same behaviour as register_hparams."""

  def decorator(ap_fn, registration_name=None):
    """Registers & returns ap_fn with registration_name or default name."""
    ap_name = registration_name or default_name(ap_fn)
    if ap_name in _ATTACK_PARAMS and not tf.contrib.eager.in_eager_mode():
      raise LookupError("Attack HParams set %s already registered." % ap_name)
    _ATTACK_PARAMS[ap_name] = ap_fn
    return ap_fn

  # Handle if decorator was used without parens
  if callable(name):
    ap_fn = name
    return decorator(ap_fn, registration_name=default_name(ap_fn))

  return lambda ap_fn: decorator(ap_fn, name)


def attack_params(name):
  """Retrieve registered aparams by name."""
  if name not in _ATTACK_PARAMS:
    error_msg = "Attack HParams set %s never registered. Sets registered:\n%s"
    raise LookupError(
        error_msg %
        (name, display_list_by_prefix(list_attack_params(), starting_spaces=4)))
  ap = _ATTACK_PARAMS[name]()
  if ap is None:
    raise TypeError("Attack HParams %s is None. Make sure the registered "
                    "function returns the HParams object." % name)
  return ap


def list_attack_params(prefix=None):
  if prefix:
    return [name for name in _ATTACK_PARAMS if name.startswith(prefix)]
  return list(_ATTACK_PARAMS)


def _internal_get_modality(name, mod_collection, collection_str):
  if name is None:
    name = "default"
  if name not in mod_collection:
    raise LookupError(
        "%s modality %s never registered." % (collection_str, name))
  return mod_collection[name]


def symbol_modality(name=None):
  return _internal_get_modality(name, _MODALITIES[Modalities.SYMBOL],
                                Modalities.SYMBOL.capitalize())


def generic_modality(name=None):
  return _internal_get_modality(name, _MODALITIES[Modalities.GENERIC],
                                Modalities.GENERIC.capitalize())


def video_modality(name=None):
  return _internal_get_modality(name, _MODALITIES[Modalities.VIDEO],
                                Modalities.VIDEO.capitalize())


def audio_modality(name=None):
  return _internal_get_modality(name, _MODALITIES[Modalities.AUDIO],
                                Modalities.AUDIO.capitalize())


def image_modality(name=None):
  return _internal_get_modality(name, _MODALITIES[Modalities.IMAGE],
                                Modalities.IMAGE.capitalize())


def class_label_modality(name=None):
  return _internal_get_modality(name, _MODALITIES[Modalities.CLASS_LABEL],
                                Modalities.CLASS_LABEL.capitalize())


def real_modality(name=None):
  return _internal_get_modality(name, _MODALITIES[Modalities.REAL],
                                Modalities.REAL.capitalize())


def _internal_register_modality(name, mod_collection, collection_str):
  """Register a modality into mod_collection."""

  def decorator(mod_cls, registration_name=None):
    """Registers & returns mod_cls with registration_name or default name."""
    mod_name = registration_name or default_name(mod_cls)
    if mod_name in mod_collection and not tf.contrib.eager.in_eager_mode():
      raise LookupError(
          "%s modality %s already registered." % (collection_str, mod_name))
    mod_collection[mod_name] = mod_cls
    return mod_cls

  # Handle if decorator was used without parens
  if callable(name):
    mod_cls = name
    return decorator(mod_cls, registration_name=default_name(mod_cls))

  return lambda mod_cls: decorator(mod_cls, name)


def register_symbol_modality(name=None):
  """Register a symbol modality. name defaults to class name snake-cased."""
  return _internal_register_modality(name, _MODALITIES[Modalities.SYMBOL],
                                     Modalities.SYMBOL.capitalize())


def register_generic_modality(name=None):
  """Register a generic modality. name defaults to class name snake-cased."""
  return _internal_register_modality(name, _MODALITIES[Modalities.GENERIC],
                                     Modalities.GENERIC.capitalize())


def register_real_modality(name=None):
  """Register a real modality. name defaults to class name snake-cased."""
  return _internal_register_modality(name, _MODALITIES[Modalities.REAL],
                                     Modalities.REAL.capitalize())


def register_audio_modality(name=None):
  """Register an audio modality. name defaults to class name snake-cased."""
  return _internal_register_modality(name, _MODALITIES[Modalities.AUDIO],
                                     Modalities.AUDIO.capitalize())


def register_image_modality(name=None):
  """Register an image modality. name defaults to class name snake-cased."""
  return _internal_register_modality(name, _MODALITIES[Modalities.IMAGE],
                                     Modalities.IMAGE.capitalize())


def register_video_modality(name=None):
  """Register a video modality. name defaults to class name snake-cased."""
  return _internal_register_modality(name, _MODALITIES[Modalities.VIDEO],
                                     Modalities.VIDEO.capitalize())


def register_class_label_modality(name=None):
  """Register an image modality. name defaults to class name snake-cased."""
  return _internal_register_modality(name, _MODALITIES[Modalities.CLASS_LABEL],
                                     Modalities.CLASS_LABEL.capitalize())


def list_modalities():
  all_modalities = []
  for modality_type, modalities in six.iteritems(_MODALITIES):
    all_modalities.extend([
        "%s:%s" % (mtype, modality)
        for mtype, modality in zip([modality_type] *
                                   len(modalities), modalities)
    ])
  return all_modalities


def parse_modality_name(name):
  name_parts = name.split(":")
  if len(name_parts) < 2:
    name_parts.append("default")
  modality_type, modality_name = name_parts
  return modality_type, modality_name


def create_modality(modality_spec, model_hparams):
  """Create modality.

  Args:
    modality_spec: tuple, ("modality_type:modality_name", vocab_size).
    model_hparams: HParams object.

  Returns:
    Modality instance.

  Raises:
    LookupError: if modality_type is not recognized. See Modalities class for
    accepted types.
  """
  retrieval_fns = {
      Modalities.SYMBOL: symbol_modality,
      Modalities.IMAGE: image_modality,
      Modalities.AUDIO: audio_modality,
      Modalities.VIDEO: video_modality,
      Modalities.CLASS_LABEL: class_label_modality,
      Modalities.GENERIC: generic_modality,
      Modalities.REAL: real_modality,
  }

  modality_full_name, vocab_size = modality_spec
  modality_type, modality_name = parse_modality_name(modality_full_name)
  if modality_type not in retrieval_fns:
    raise LookupError("Modality type %s not recognized. Options are: %s" %
                      (modality_type, list(_MODALITIES)))

  return retrieval_fns[modality_type](modality_name)(model_hparams, vocab_size)


def display_list_by_prefix(names_list, starting_spaces=0):
  """Creates a help string for names_list grouped by prefix."""
  cur_prefix, result_lines = None, []
  space = " " * starting_spaces
  for name in sorted(names_list):
    split = name.split("_", 1)
    prefix = split[0]
    if cur_prefix != prefix:
      result_lines.append(space + prefix + ":")
      cur_prefix = prefix
    result_lines.append(space + "  * " + name)
  return "\n".join(result_lines)


def help_string():
  """Generate help string with contents of registry."""
  help_str = """
Registry contents:
------------------

  Models:
%s

  HParams:
%s

  RangedHParams:
%s

  Modalities:
%s

  Problems:
%s

  Attacks:
%s

  Attack HParams:
%s
"""
  m, hp, rhp, mod, probs, atks, ap = [
      display_list_by_prefix(entries, starting_spaces=4) for entries in [
          list_models(),
          list_hparams(),
          list_ranged_hparams(),
          list_modalities(),
          list_problems(),
          list_attacks(),
          list_attack_params()
      ]
  ]
  return help_str % (m, hp, rhp, mod, probs, atks, ap)
