#include "pack_img.h"

extern const uint8_t pack_frames_map[];

#define PACK_FRAME_BYTES (240 * 240 * 2)

const lv_img_dsc_t pack_img[4] = {
    {
        .header.always_zero = 0,
        .header.w = 240,
        .header.h = 240,
        .header.cf = LV_IMG_CF_TRUE_COLOR,
        .data_size = PACK_FRAME_BYTES,
        .data = pack_frames_map + PACK_FRAME_BYTES * 0,
    },
    {
        .header.always_zero = 0,
        .header.w = 240,
        .header.h = 240,
        .header.cf = LV_IMG_CF_TRUE_COLOR,
        .data_size = PACK_FRAME_BYTES,
        .data = pack_frames_map + PACK_FRAME_BYTES * 1,
    },
    {
        .header.always_zero = 0,
        .header.w = 240,
        .header.h = 240,
        .header.cf = LV_IMG_CF_TRUE_COLOR,
        .data_size = PACK_FRAME_BYTES,
        .data = pack_frames_map + PACK_FRAME_BYTES * 2,
    },
    {
        .header.always_zero = 0,
        .header.w = 240,
        .header.h = 240,
        .header.cf = LV_IMG_CF_TRUE_COLOR,
        .data_size = PACK_FRAME_BYTES,
        .data = pack_frames_map + PACK_FRAME_BYTES * 3,
    },
};
