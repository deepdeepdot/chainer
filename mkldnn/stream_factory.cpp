#include <glog/logging.h>
#include <iostream>
#include "mkldnn.hpp"
#include "stream_factory.h"

// helper functions to convert layer unique data to a string
static std::string pointer_to_string(void* ptr)
{
    std::ostringstream os;
    os << std::hex << static_cast<void*>(ptr) << "_";
    return os.str();
}
// end of helper functions

mkldnn::stream* StreamFactory::getStream(std::string key)
{
    auto stream_iter = map.find(key);
    if (stream_iter == map.end()) {
        return NULL;
    } else {
        return stream_iter->second;
    }
}

void StreamFactory::setStream(std::string key, mkldnn::stream* stream)
{
    auto stream_iter = map.find(key);
    if (stream_iter == map.end()) {
        map[key]=stream;
    } else {
        throw new std::invalid_argument("cannot set same key to a new stream");
    }
}

#define RELU_FWD_PREFIX "relu_fwd_"
#define RELU_BWD_PREFIX "relu_bwd_"

mkldnn::stream* StreamFactory::getRELUFwdStream(void* input)
{
    std::string key = RELU_FWD_PREFIX;

    key += pointer_to_string(input);
    return getStream(key);
}

void StreamFactory::setRELUFwdStream(void* input, mkldnn::stream* stream)
{
    std::string key = RELU_FWD_PREFIX;

    key += pointer_to_string(input);
    setStream(key, stream);
}

mkldnn::stream* StreamFactory::getRELUBwdStream(
        void* input, void* output_diff, void* input_diff)
{
    std::string key = RELU_BWD_PREFIX;

    key += pointer_to_string(input);
    key += pointer_to_string(output_diff);
    key += pointer_to_string(input_diff);
    return getStream(key);
}

void StreamFactory::setRELUBwdStream(
        void* input, void* output_diff, void* input_diff,
        mkldnn::stream* stream)
{
    std::string key = RELU_BWD_PREFIX;

    key += pointer_to_string(input);
    key += pointer_to_string(output_diff);
    key += pointer_to_string(input_diff);
    setStream(key, stream);
}
