#!/usr/bin/env python

"""Generate c++ and LCM definitions for the LCM Vector concept.
"""

import argparse
import os
import subprocess


def put(fileobj, text, newlines_after=0):
    fileobj.write(text.strip('\n') + '\n' * newlines_after)


INDICES_BEGIN = """
/// Describes the row indices of a %(camel)s.
struct DRAKECARS_EXPORT %(indices)s {
  /// The total number of rows (coordinates).
  static const int kNumCoordinates = %(nfields)d;

  // The index of each individual coordinate.
"""
INDICES_FIELD = """static const int %(kname)s = %(kvalue)d;"""
INDICES_FIELD_STORAGE = """const int %(indices)s::%(kname)s;"""
INDICES_END = """
};
"""

def to_kname(field):
    return 'k' + ''.join([
        word.capitalize()
        for word in field.split('_')])

def generate_indices(hh, caller_context, fields):
    """
    Args:
        fields is the list of fieldnames in the LCM message.
    """
    context = dict(caller_context)
    context.update(nfields = len(fields))
    context.update(kname = "kNumCoordinates")
    put(hh, INDICES_BEGIN % context, 1)
    for kvalue, field in enumerate(fields):
        # field is the LCM message field name
        # kname is the C++ kConstant name
        # kvalue is the C++ vector row index integer value
        context.update(kname = to_kname(field))
        context.update(kvalue = kvalue)
        put(hh, INDICES_FIELD % context, 1)
    put(hh, INDICES_END % context, 2)

def generate_indices_storage(cc, caller_context, fields):
    """
    Args:
        fields is the list of fieldnames in the LCM message.
    """
    context = dict(caller_context)
    context.update(nfields = len(fields))
    context.update(kname = "kNumCoordinates")
    put(cc, INDICES_FIELD_STORAGE % context, 1)
    for kvalue, field in enumerate(fields):
        # field is the LCM message field name
        # kname is the C++ kConstant name
        # kvalue is the C++ vector row index integer value
        context.update(kname = to_kname(field))
        context.update(kvalue = kvalue)
        put(cc, INDICES_FIELD_STORAGE % context, 1)
    put(cc, '', 1)


DEFAULT_CTOR = """
  /// Default constructor.  Sets all rows to zero.
  %(camel)s() : systems::BasicVector<T>(K::kNumCoordinates) {
    this->SetFromVector(VectorX<T>::Zero(K::kNumCoordinates));
  }
"""

def generate_default_ctor(hh, context, _):
    put(hh, DEFAULT_CTOR % context, 2)


ACCESSOR_BEGIN = """
  /// @name Getters and Setters
  //@{
"""
ACCESSOR = """
    const T %(field)s() const { return this->GetAtIndex(K::%(kname)s); }
    void set_%(field)s(const T& %(field)s) {
      this->SetAtIndex(K::%(kname)s, %(field)s);
    }
"""
ACCESSOR_END = """
  //@}
"""

def generate_accessors(hh, caller_context, fields):
    context = dict(caller_context)
    put(hh, ACCESSOR_BEGIN % context, 1)
    for field in fields:
        context.update(field = field)
        context.update(kname = to_kname(field))
        put(hh, ACCESSOR % context, 1)
    put(hh, ACCESSOR_END % context, 2)

ENCODE_BEGIN = """
template <typename ScalarType>
bool encode(const double& t, const %(camel)s<ScalarType>& wrap,
            // NOLINTNEXTLINE(runtime/references)
            drake::lcmt_%(snake)s_t& msg) {
  msg.timestamp = static_cast<int64_t>(t * 1000);
"""
ENCODE_FIELD = """  msg.%(field)s = wrap.%(field)s();"""
ENCODE_END = """
  return true;
}
"""


def generate_encode(hh, caller_context, fields):
    context = dict(caller_context)
    put(hh, ENCODE_BEGIN % context, 1)
    for field in fields:
        context.update(field = field)
        put(hh, ENCODE_FIELD % context, 1)
    put(hh, ENCODE_END % context, 2)


DECODE_BEGIN = """
template <typename ScalarType>
bool decode(const drake::lcmt_%(snake)s_t& msg,
            // NOLINTNEXTLINE(runtime/references)
            double& t,
            // NOLINTNEXTLINE(runtime/references)
            %(camel)s<ScalarType>& wrap) {
  t = static_cast<double>(msg.timestamp) / 1000.0;
"""
DECODE_FIELD = """  wrap.set_%(field)s(msg.%(field)s);"""
DECODE_END = """
  return true;
}
"""


def generate_decode(hh, caller_context, fields):
    context = dict(caller_context)
    put(hh, DECODE_BEGIN % context, 1)
    for k, field in enumerate(fields):
        context.update(field = field)
        put(hh, DECODE_FIELD % context, 1)
    put(hh, DECODE_END % context, 2)


VECTOR_HH_PREAMBLE = """
#pragma once

// This file is generated by a script.  Do not edit!
// See %(generator)s.

#include <stdexcept>
#include <string>

#include <Eigen/Core>

#include "drake/drakeCars_export.h"
#include "drake/systems/framework/basic_vector.h"
#include "lcmtypes/drake/lcmt_%(snake)s_t.hpp"

namespace drake {
namespace cars {
"""

VECTOR_CLASS_BEGIN = """

/// Specializes BasicVector with specific getters and setters.
template <typename T>
class %(camel)s : public systems::BasicVector<T> {
 public:
  // An abbreviation for our row index constants.
  typedef %(indices)s K;
"""

VECTOR_CLASS_END = """
  /// @name Implement the LCMVector concept
  //@{
  typedef drake::lcmt_%(snake)s_t LCMMessageType;
  static std::string channel() { return "%(screaming_snake)s"; }
  //@}
};
"""

VECTOR_HH_POSTAMBLE = """
}  // namespace cars
}  // namespace drake
"""

VECTOR_CC_PREAMBLE = """
#include "drake/examples/Cars/gen/%(snake)s.h"

// This file is generated by a script.  Do not edit!
// See %(generator)s.

namespace drake {
namespace cars {
"""

VECTOR_CC_POSTAMBLE = """
}  // namespace cars
}  // namespace drake
"""

TRANSLATOR_HH_PREAMBLE = """
#pragma once

// This file is generated by a script.  Do not edit!
// See %(generator)s.

#include "drake/drakeCars_export.h"
#include "drake/examples/Cars/gen/%(snake)s.h"
#include "drake/systems/lcm/lcm_and_vector_base_translator.h"
#include "lcmtypes/drake/lcmt_%(snake)s_t.hpp"

namespace drake {
namespace cars {
"""

TRANSLATOR_CLASS_DECL = """
/**
 * Translates between LCM message objects and VectorBase objects for the
 * %(camel)s type.
 */
class DRAKECARS_EXPORT %(camel)sTranslator
    : public systems::lcm::LcmAndVectorBaseTranslator {
 public:
  %(camel)sTranslator()
      : LcmAndVectorBaseTranslator(%(indices)s::kNumCoordinates) {}
  std::unique_ptr<systems::BasicVector<double>> AllocateOutputVector()
      const override;
  void TranslateLcmToVectorBase(
      const void* lcm_message_bytes, int lcm_message_length,
      systems::VectorBase<double>* vector_base) const override;
  void TranslateVectorBaseToLcm(
      const systems::VectorBase<double>& vector_base,
      std::vector<uint8_t>* lcm_message_bytes) const override;
};
"""

TRANSLATOR_HH_POSTAMBLE = """
}  // namespace cars
}  // namespace drake
"""

TRANSLATOR_CC_PREAMBLE = """
#include "drake/examples/Cars/gen/%(snake)s_translator.h"

// This file is generated by a script.  Do not edit!
// See %(generator)s.

#include <stdexcept>

#include "drake/common/drake_assert.h"

namespace drake {
namespace cars {
"""

TRANSLATOR_CC_POSTAMBLE = """
}  // namespace cars
}  // namespace drake
"""

ALLOCATE_OUTPUT_VECTOR = """
std::unique_ptr<systems::BasicVector<double>>
%(camel)sTranslator::AllocateOutputVector() const {
  return std::make_unique<%(camel)s<double>>();
}
"""


def generate_allocate_output_vector(cc, caller_context, fields):
    context = dict(caller_context)
    put(cc, ALLOCATE_OUTPUT_VECTOR % context, 2)

LCM_TO_VECTOR_BASE_BEGIN = """
void %(camel)sTranslator::TranslateVectorBaseToLcm(
    const systems::VectorBase<double>& vector_base,
    std::vector<uint8_t>* lcm_message_bytes) const {
  const auto* const vector =
      dynamic_cast<const %(camel)s<double>*>(&vector_base);
  DRAKE_ABORT_UNLESS(vector != nullptr);
  drake::lcmt_%(snake)s_t message;
"""
LCM_FIELD_TO_VECTOR = """
  message.%(field)s = vector->%(field)s();
"""
LCM_TO_VECTOR_BASE_END = """
  const int lcm_message_length = message.getEncodedSize();
  lcm_message_bytes->resize(lcm_message_length);
  message.encode(lcm_message_bytes->data(), 0, lcm_message_length);
}
"""


def generate_lcm_to_vector_base(cc, caller_context, fields):
    context = dict(caller_context)
    put(cc, LCM_TO_VECTOR_BASE_BEGIN % context, 1)
    for field in fields:
        context.update(field = field)
        put(cc, LCM_FIELD_TO_VECTOR % context, 1)
    put(cc, LCM_TO_VECTOR_BASE_END % context, 2)

VECTOR_BASE_TO_LCM_BEGIN = """
void %(camel)sTranslator::TranslateLcmToVectorBase(
    const void* lcm_message_bytes, int lcm_message_length,
    systems::VectorBase<double>* vector_base) const {
  DRAKE_ABORT_UNLESS(vector_base != nullptr);
  auto* const my_vector = dynamic_cast<%(camel)s<double>*>(vector_base);
  DRAKE_ABORT_UNLESS(my_vector != nullptr);

  drake::lcmt_%(snake)s_t message;
  int status = message.decode(lcm_message_bytes, 0, lcm_message_length);
  if (status < 0) {
    throw std::runtime_error("Failed to decode LCM message %(snake)s.");
  }
"""
VECTOR_TO_LCM_FIELD = """  my_vector->set_%(field)s(message.%(field)s);"""
VECTOR_BASE_TO_LCM_END = """
}
"""


def generate_vector_base_to_lcm(cc, caller_context, fields):
    context = dict(caller_context)
    put(cc, VECTOR_BASE_TO_LCM_BEGIN % context, 1)
    for field in fields:
        context.update(field = field)
        put(cc, VECTOR_TO_LCM_FIELD % context, 1)
    put(cc, VECTOR_BASE_TO_LCM_END % context, 2)

LCMTYPE_PREAMBLE = """
// This file is generated by %(generator)s. Do not edit.
package drake;

struct lcmt_%(snake)s_t
{
  int64_t timestamp;

"""

LCMTYPE_POSTAMBLE = """
}
"""


def generate_code(args):
    cxx_dir = os.path.abspath(args.cxx_dir)
    lcmtype_dir = os.path.abspath(args.lcmtype_dir)
    drake_dist_dir = subprocess.check_output(
        "git rev-parse --show-toplevel".split()).strip()

    title_phrase = args.title.split()
    camel = ''.join([x.capitalize() for x in title_phrase])
    snake = '_'.join([x.lower() for x in title_phrase])
    screaming_snake = '_'.join([x.upper() for x in title_phrase])

    # The context provides string substitutions for the C++ code blocks in the
    # literal strings throughout this program.
    context = dict()
    context.update(generator = os.path.abspath(__file__).replace(
        os.path.join(drake_dist_dir, ''), ''))
    context.update(camel = camel)
    context.update(indices = camel + 'Indices')
    context.update(snake = snake)
    context.update(screaming_snake = screaming_snake)

    with open(os.path.join(cxx_dir, "%s.h" % snake), 'w') as hh:
        put(hh, VECTOR_HH_PREAMBLE % context, 2)
        generate_indices(hh, context, args.fields)
        put(hh, VECTOR_CLASS_BEGIN % context, 2)
        generate_default_ctor(hh, context, args.fields)
        generate_accessors(hh, context, args.fields)
        put(hh, VECTOR_CLASS_END % context, 2)
        generate_encode(hh, context, args.fields)
        generate_decode(hh, context, args.fields)
        put(hh, VECTOR_HH_POSTAMBLE % context, 1)

    with open(os.path.join(cxx_dir, "%s.cc" % snake), 'w') as cc:
        put(cc, VECTOR_CC_PREAMBLE % context, 2)
        generate_indices_storage(cc, context, args.fields)
        put(cc, VECTOR_CC_POSTAMBLE % context, 1)

    with open(os.path.join(cxx_dir, "%s_translator.h" % snake), 'w') as hh:
        put(hh, TRANSLATOR_HH_PREAMBLE % context, 2)
        put(hh, TRANSLATOR_CLASS_DECL % context, 2)
        put(hh, TRANSLATOR_HH_POSTAMBLE % context, 1)

    with open(os.path.join(cxx_dir, "%s_translator.cc" % snake), 'w') as cc:
        put(cc, TRANSLATOR_CC_PREAMBLE % context, 2)
        generate_allocate_output_vector(cc, context, args.fields)
        generate_lcm_to_vector_base(cc, context, args.fields)
        generate_vector_base_to_lcm(cc, context, args.fields)
        put(cc, TRANSLATOR_CC_POSTAMBLE % context, 1)

    with open(os.path.join(lcmtype_dir, "lcmt_%s_t.lcm" % snake), 'w') as lcm:
        put(lcm, LCMTYPE_PREAMBLE % context, 1)
        for field in args.fields:
            put(lcm, "  double %s;" % field, 1)
        put(lcm, LCMTYPE_POSTAMBLE % context, 1)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '--cxx-dir', help="output directory for cxx files", default=".")
    parser.add_argument(
        '--lcmtype-dir', help="output directory for lcm file", default=".")
    parser.add_argument(
        '--title', help="title phrase, from which type names will be made")
    parser.add_argument(
        'fields', metavar='FIELD', nargs='+', help="field names for vector")
    args = parser.parse_args()
    generate_code(args)

if __name__ == "__main__":
    main()
