#pragma once
#include <stdint.h>

struct OracleLot {
    uint8_t num;   /* 1..100 */
    uint8_t grade; /* 0上上 1上吉 2中吉 3中平 4中下 5下下 */
    const char *verse;
};

#define ORACLE_LOT_COUNT 100
extern const OracleLot kOracleLots[ORACLE_LOT_COUNT];
extern const char *const kOracleGrade[6];
extern const uint32_t kOracleGradeCol[6];
