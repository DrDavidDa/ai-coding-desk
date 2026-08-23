#pragma once

#include <lvgl.h>



#ifdef __cplusplus

extern "C" {

#endif



enum { WALL_COUNT = 6 };



extern const lv_img_dsc_t kWallImgs[WALL_COUNT];



/* Backward compat — wave is index 0. */

#define wave_bg_img kWallImgs[0]



static inline const lv_img_dsc_t *wall_img_get(uint8_t id) {

    if (id >= WALL_COUNT) id = 0;

    return &kWallImgs[id];

}



#ifdef __cplusplus

}

#endif

