#include "wave_img.h"



extern const uint8_t wave_bg_map[];

extern const uint8_t wall_ember_map[];

extern const uint8_t wall_ink_map[];

extern const uint8_t wall_phosphor_map[];

extern const uint8_t wall_night_map[];

extern const uint8_t wall_stone_map[];



#define WALL_BYTES (240 * 240 * 2)



const lv_img_dsc_t kWallImgs[WALL_COUNT] = {

    {

        .header.always_zero = 0,

        .header.w = 240,

        .header.h = 240,

        .header.cf = LV_IMG_CF_TRUE_COLOR,

        .data_size = WALL_BYTES,

        .data = wave_bg_map,

    },

    {

        .header.always_zero = 0,

        .header.w = 240,

        .header.h = 240,

        .header.cf = LV_IMG_CF_TRUE_COLOR,

        .data_size = WALL_BYTES,

        .data = wall_ember_map,

    },

    {

        .header.always_zero = 0,

        .header.w = 240,

        .header.h = 240,

        .header.cf = LV_IMG_CF_TRUE_COLOR,

        .data_size = WALL_BYTES,

        .data = wall_ink_map,

    },

    {

        .header.always_zero = 0,

        .header.w = 240,

        .header.h = 240,

        .header.cf = LV_IMG_CF_TRUE_COLOR,

        .data_size = WALL_BYTES,

        .data = wall_phosphor_map,

    },

    {

        .header.always_zero = 0,

        .header.w = 240,

        .header.h = 240,

        .header.cf = LV_IMG_CF_TRUE_COLOR,

        .data_size = WALL_BYTES,

        .data = wall_night_map,

    },

    {

        .header.always_zero = 0,

        .header.w = 240,

        .header.h = 240,

        .header.cf = LV_IMG_CF_TRUE_COLOR,

        .data_size = WALL_BYTES,

        .data = wall_stone_map,

    },

};

