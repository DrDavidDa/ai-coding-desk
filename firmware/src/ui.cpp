#include "ui.h"
#include "status.h"
#include "board.h"
#include "voice.h"
#include "hid_keys.h"
#include "beep.h"
#include "net.h"
#include "config.h"
#include "pack_img.h"
#include "logos_img.h"
#include "fonts/font_idle.h"
#include "fonts/font_icons.h"
#include "display.h"
#include <Arduino.h>
#include <lvgl.h>
#include <cstdio>
#include <cstring>
#include <ctime>

enum UiPage { PAGE_DESK = 0, PAGE_USAGE, PAGE_PACK, PAGE_IDLE, PAGE_PLAN, PAGE_COUNT };
static const uint32_t kIdleMs = 180000;

static const lv_color_t C_BG = lv_color_hex(0x100E0C);
static const lv_color_t C_INK = lv_color_hex(0xF1E6D4);
static const lv_color_t C_MUTE = lv_color_hex(0x8D8274);
static const lv_color_t C_COPPER = lv_color_hex(0xD4A06A);
static const lv_color_t C_HOT = lv_color_hex(0xC45C3A);
static const lv_color_t C_ORANGE = lv_color_hex(0xE87B1A);
static const lv_color_t C_WELL = lv_color_hex(0x2A2622);
static const lv_color_t C_WHITE = lv_color_hex(0xFFFFFF);
static const lv_color_t C_GOLD = lv_color_hex(0xF0C14A);
static const lv_color_t C_PACK_LAB = lv_color_hex(0xFFF8E8);
static const lv_color_t C_PACK_AMT = lv_color_hex(0xFFE04E);
static const lv_color_t C_PACK_SPARK = lv_color_hex(0xFFE35A);
static const lv_color_t C_GRAY = lv_color_hex(0x6A645C);
static const lv_color_t C_IDLE = lv_color_hex(0x090807);
static const lv_color_t C_PLAN = lv_color_hex(0x0E0C0B);
static const lv_color_t C_PLUS = lv_color_hex(0x74FF7A);
static const lv_color_t C_STOP_REC = lv_color_hex(0x241C16);
static const lv_color_t C_LAMP = lv_color_hex(0xD8D0C4);
static const lv_color_t C_TALK = lv_color_hex(0x7EC8FF);
static const lv_color_t C_RUN = lv_color_hex(0x3D7DFF);
static const lv_color_t C_TIME = lv_color_hex(0xF1E6D4);

enum { BR_MONO = 1, BR_INK = 2 };

struct BrandMeta {
    const char *id;
    const char *name;
    uint32_t color;
    uint8_t flags;
    int tokens;
    const char *upd;
    uint32_t reset_s;
};

/* Same order as docs/desk154-live.html BRANDS / logo_img[]. */
static const BrandMeta kBrands[LOGO_COUNT] = {
    {"codex", "CODEX", 0xE8E4DC, BR_MONO, 420000, "TODAY 09:12", 6 * 3600 + 22 * 60},
    {"claude", "CLAUDE", 0xD97757, 0, 890000, "TODAY 10:04", 2 * 3600 + 40 * 60},
    {"deepseek", "DEEPSEEK", 0x4D6BFE, 0, 210000, "TODAY 08:51", 11 * 3600},
    {"cursor", "CURSOR", 0xF2EDE4, BR_MONO, -1, "TODAY 09:40", 4 * 3600 + 12 * 60},
    {"glm", "GLM", 0x4A7DFF, 0, 1240000, "TODAY 10:01", 18 * 3600 + 5 * 60},
    {"kimi", "KIMI", 0xC4B8A8, BR_INK, -1, "TODAY 07:18", 50 * 60},
    {"trae", "TRAE", 0x32F08C, 0, -1, "YDAY 22:10", 3 * 86400},
    {"coze", "COZE", 0x6B4CFF, 0, -1, "TODAY 09:55", 7 * 3600 + 10 * 60},
    {"copilot", "COPILOT", 0xE8E4DC, BR_MONO, -2, "TODAY 08:10", 0},
    {"windsurf", "WINDSURF", 0x7EC8FF, BR_MONO, -2, "TODAY 09:13", 0},
    {"mscopilot", "MS COPILOT", 0x00AEFF, 0, -2, "TODAY 10:16", 0},
    {"gemini", "GEMINI", 0x3186FF, 0, -2, "TODAY 08:19", 0},
    {"antigravity", "GRAVITY", 0xFFE432, 0, -2, "TODAY 09:22", 0},
    {"geminicli", "GEMCLI", 0xE8E4DC, BR_MONO, -2, "TODAY 10:25", 0},
    {"junie", "JUNIE", 0x47E054, 0, -2, "TODAY 08:28", 0},
    {"devin", "DEVIN", 0x3969CA, 0, -2, "TODAY 09:31", 0},
    {"replit", "REPLIT", 0xFD5402, 0, -2, "TODAY 10:34", 0},
    {"v0", "V0", 0xF2EDE4, BR_MONO, -2, "TODAY 08:37", 0},
    {"lovable", "LOVABLE", 0xFE7B02, 0, -2, "TODAY 09:40", 0},
    {"codebuddy", "CBUDDY", 0x6C4DFF, 0, -2, "TODAY 10:43", 0},
    {"qoder", "QODER", 0x2ADB5C, 0, -2, "TODAY 08:46", 0},
    {"kiro", "KIRO", 0x9046FF, 0, -2, "TODAY 09:49", 0},
    {"amp", "AMP", 0xF34E3F, 0, -2, "TODAY 10:52", 0},
    {"kilocode", "KILO", 0xE8E4DC, BR_MONO, -2, "TODAY 08:55", 0},
    {"cline", "CLINE", 0xF2EDE4, BR_MONO, -2, "TODAY 09:58", 0},
    {"roocode", "ROO", 0xE8E4DC, BR_MONO, -2, "TODAY 10:01", 0},
    {"opencode", "OPENCODE", 0xF2EDE4, BR_MONO, -2, "TODAY 08:04", 0},
    {"codegeex", "CODEGEEX", 0x00BFFF, 0, -2, "TODAY 09:07", 0},
    {"phind", "PHIND", 0xE8E4DC, BR_MONO, -2, "TODAY 10:10", 0},
    {"greptile", "GREPTILE", 0x44A775, 0, -2, "TODAY 08:13", 0},
    {"poolside", "POOLSIDE", 0x4137FF, 0, -2, "TODAY 09:16", 0},
    {"kwaipilot", "KAT", 0xFF6A00, 0, -2, "TODAY 10:19", 0},
    {"goose", "GOOSE", 0xE8E4DC, BR_MONO, -2, "TODAY 08:22", 0},
    {"zencoder", "ZENCODER", 0xE65C2C, 0, -2, "TODAY 09:25", 0},
    {"aws", "AMAZON Q", 0xFF9900, 0, -2, "TODAY 10:28", 0},
};

static int sPage = PAGE_DESK;
static int sUsagePage = 0;
static int sPlanIdx = -1;
static bool sPackFromUsage = false;
static lv_obj_t *sScreens[PAGE_COUNT];
static int16_t sSwipeX = -1;
static int16_t sSwipeY = -1;
static int16_t sSwipeAbs = 0;
static bool sIdlePress = false;

static lv_obj_t *sLine = nullptr;
static lv_obj_t *sTalkHalo = nullptr;
static lv_obj_t *sTalkBtn = nullptr;
static lv_obj_t *sStopBtn = nullptr;
static lv_obj_t *sTalkLab = nullptr;
static lv_obj_t *sStopLab = nullptr;
static lv_obj_t *sKey[3] = {};
static lv_obj_t *sKeyAct[3] = {};
static lv_obj_t *sDeskBar = nullptr;
static lv_obj_t *sLamp = nullptr;
static lv_obj_t *sToast = nullptr;
static lv_obj_t *sDots[2] = {};

static lv_obj_t *sCell[4] = {};
static lv_obj_t *sMark[4] = {};
static lv_obj_t *sGray[4] = {};
static lv_obj_t *sClip[4] = {};
static lv_obj_t *sColor[4] = {};
static lv_obj_t *sCd[4] = {};
static lv_obj_t *sPager = nullptr;
static lv_obj_t *sPagerNum = nullptr;

static lv_obj_t *sIdleDate = nullptr;
static lv_obj_t *sIdleBat = nullptr;
static lv_obj_t *sIdleBatRow = nullptr;
static lv_obj_t *sIdleBatIcon = nullptr;
static lv_obj_t *sIdleBatFill = nullptr;
static lv_obj_t *sIdleBatNub = nullptr;
static lv_obj_t *sIdleTime = nullptr;

static lv_obj_t *sPlanGhost = nullptr;
static lv_obj_t *sPlanBack = nullptr;
static lv_obj_t *sPlanName = nullptr;
static lv_obj_t *sPlanUpd = nullptr;
static lv_obj_t *sPlanLab[3] = {};
static lv_obj_t *sPlanPct[3] = {};
static lv_obj_t *sPlanFill[3] = {};
static lv_obj_t *sPlanTrack[3] = {};
static lv_obj_t *sPlanFoot = nullptr;

static lv_obj_t *sPackImg = nullptr;
static lv_obj_t *sPackTotal = nullptr;
static lv_obj_t *sPackPlus = nullptr;
static lv_obj_t *sPackQueue[8] = {};

static uint32_t sHintUntil = 0;
static uint32_t sActAt = 0;
static uint32_t sResetTickAt = 0;
static uint32_t sBlinkAt = 0;
static bool sBlinkOn = true;
static uint32_t sPackTokens = 0;
static uint32_t sPackSaveAt = 0;
static uint32_t sPackPlusUntil = 0;
static uint32_t sPackStepAt = 0;
static uint32_t sPackHold = 0;
static uint32_t sPackRng = 0xC05EED;
static uint8_t sPackPending = 0;
static uint8_t sPackStep = 0;
static uint8_t sPackFrame = 0;
static bool sPackBusy = false;
static bool sPackKnocked = false;
static bool sPackDidReset = false;
static char sFlash[24] = {0};

static int sRemain[LOGO_COUNT];
static int sPrevRemain[LOGO_COUNT];
static int sH5[LOGO_COUNT];
static int sD7[LOGO_COUNT];
static int sD30[LOGO_COUNT];
static int sTokens[LOGO_COUNT];
static uint32_t sReset[LOGO_COUNT];
static bool sOn[LOGO_COUNT];
static bool sLive[LOGO_COUNT];

static void show_current();
static void usage_paint();
static void idle_paint();
static void plan_paint();
static void wake_idle();
static void paint_lamp();
static void brand_sync_live();
static int clamp100(int v);

static void paint_scr(lv_obj_t *scr, lv_color_t bg) {
    lv_obj_set_style_bg_color(scr, bg, 0);
    lv_obj_set_style_bg_opa(scr, LV_OPA_COVER, 0);
    lv_obj_clear_flag(scr, LV_OBJ_FLAG_SCROLLABLE);
}

static lv_obj_t *make_label(lv_obj_t *p, const lv_font_t *font, lv_color_t col) {
    lv_obj_t *l = lv_label_create(p);
    lv_obj_set_style_text_font(l, font, 0);
    lv_obj_set_style_text_color(l, col, 0);
    return l;
}

static lv_obj_t *make_rect(lv_obj_t *p, lv_coord_t w, lv_coord_t h, lv_color_t c) {
    lv_obj_t *o = lv_obj_create(p);
    lv_obj_set_size(o, w, h);
    lv_obj_set_style_bg_color(o, c, 0);
    lv_obj_set_style_bg_opa(o, LV_OPA_COVER, 0);
    lv_obj_set_style_border_width(o, 0, 0);
    lv_obj_set_style_radius(o, 0, 0);
    lv_obj_set_style_pad_all(o, 0, 0);
    lv_obj_clear_flag(o, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_clear_flag(o, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_clear_flag(o, LV_OBJ_FLAG_OVERFLOW_VISIBLE);
    return o;
}

static void style_hit(lv_obj_t *b, lv_color_t bg) {
    lv_obj_set_style_bg_color(b, bg, LV_PART_MAIN);
    lv_obj_set_style_bg_opa(b, LV_OPA_COVER, LV_PART_MAIN);
    lv_obj_set_style_border_width(b, 0, LV_PART_MAIN);
    lv_obj_set_style_pad_all(b, 0, LV_PART_MAIN);
    lv_obj_set_style_radius(b, 0, LV_PART_MAIN);
}

static lv_obj_t *make_hit(lv_obj_t *parent, lv_coord_t w, lv_coord_t h, lv_color_t bg, lv_event_cb_t cb) {
    lv_obj_t *b = lv_obj_create(parent);
    lv_obj_remove_style_all(b);
    lv_obj_set_size(b, w, h);
    style_hit(b, bg);
    lv_obj_add_flag(b, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_clear_flag(b, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_clear_flag(b, LV_OBJ_FLAG_EVENT_BUBBLE);
    if (cb) lv_obj_add_event_cb(b, cb, LV_EVENT_CLICKED, nullptr);
    return b;
}

static const lv_coord_t kBatIconW = 20;
static const lv_coord_t kBatIconH = 11;
static const lv_coord_t kBatFillMax = 16;
static const lv_coord_t kBatRowW = 88;
static const lv_coord_t kBatRowH = 20;

static void make_bat_row(lv_obj_t *scr, lv_color_t bg, lv_obj_t **row, lv_obj_t **icon,
                         lv_obj_t **fill, lv_obj_t **nub, lv_obj_t **lab) {
    *row = lv_obj_create(scr);
    lv_obj_remove_style_all(*row);
    lv_obj_set_size(*row, kBatRowW, kBatRowH);
    lv_obj_clear_flag(*row, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_clear_flag(*row, LV_OBJ_FLAG_CLICKABLE);
    *icon = make_rect(*row, kBatIconW, kBatIconH, bg);
    lv_obj_set_style_border_width(*icon, 1, 0);
    lv_obj_set_style_border_color(*icon, C_MUTE, 0);
    lv_obj_set_pos(*icon, 0, 5);
    *fill = make_rect(*icon, 10, 5, C_MUTE);
    lv_obj_align(*fill, LV_ALIGN_LEFT_MID, 2, 0);
    *nub = make_rect(*row, 3, 5, C_MUTE);
    lv_obj_set_pos(*nub, kBatIconW, 8);
    *lab = make_label(*row, &lv_font_montserrat_16, C_MUTE);
    lv_label_set_text(*lab, "--");
    lv_obj_set_width(*lab, 58);
    lv_label_set_long_mode(*lab, LV_LABEL_LONG_CLIP);
    lv_obj_set_pos(*lab, kBatIconW + 6, 1);
}

static void paint_one_bat(lv_obj_t *lab, lv_obj_t *icon, lv_obj_t *nub, lv_obj_t *fill, lv_color_t normal) {
    int pct = gStatus.battery_pct;
    char b[12];
    if (pct < 0) snprintf(b, sizeof(b), "--");
    else if (gStatus.charging) snprintf(b, sizeof(b), "%d%%+", pct);
    else snprintf(b, sizeof(b), "%d%%", pct);
    lv_color_t c = (pct >= 0 && pct <= 15) ? C_HOT : normal;
    if (lab) {
        lv_label_set_text(lab, b);
        lv_obj_set_style_text_color(lab, c, 0);
    }
    if (icon) lv_obj_set_style_border_color(icon, c, 0);
    if (nub) lv_obj_set_style_bg_color(nub, c, 0);
    if (fill) {
        int w = pct < 0 ? 5 : (1 + (kBatFillMax * clamp100(pct)) / 100);
        if (w < 1) w = 1;
        lv_obj_set_width(fill, w);
        lv_obj_set_style_bg_color(fill, c, 0);
    }
}

static void pack_load() {
    gPrefs.begin("desk154", true);
    sPackTokens = gPrefs.getUInt("pack_tok", 0);
    gPrefs.end();
}

static void pack_save() {
    gPrefs.begin("desk154", false);
    gPrefs.putUInt("pack_tok", sPackTokens);
    gPrefs.end();
}

static void format_tokens(uint32_t n, char *out, size_t cap) {
    static const char *units[] = {"", "K", "M", "B", "T"};
    if (n < 1000) {
        snprintf(out, cap, "0K");
        return;
    }
    double v = (double)n;
    int u = 0;
    while (v >= 1000.0 && u < 4) {
        v /= 1000.0;
        u++;
    }
    if (u == 0) {
        snprintf(out, cap, "%lu", (unsigned long)n);
        return;
    }
    int tenth = (int)(v * 10.0 + 0.5);
    if (tenth >= 10000 && u < 4) {
        tenth = (tenth + 5) / 10;
        u++;
    }
    if (tenth % 10 == 0) snprintf(out, cap, "%d%s", tenth / 10, units[u]);
    else snprintf(out, cap, "%d.%d%s", tenth / 10, tenth % 10, units[u]);
}

static void pack_show(uint8_t frame) {
    sPackFrame = frame;
    if (sPackImg) lv_img_set_src(sPackImg, &pack_img[frame]);
}

static void pack_draw_total() {
    if (!sPackTotal) return;
    char b[16];
    format_tokens(sPackTokens, b, sizeof(b));
    lv_label_set_text(sPackTotal, b);
}

static void pack_draw_queue() {
    for (int i = 0; i < 8; i++) {
        if (!sPackQueue[i]) continue;
        if (i < sPackPending) lv_obj_clear_flag(sPackQueue[i], LV_OBJ_FLAG_HIDDEN);
        else lv_obj_add_flag(sPackQueue[i], LV_OBJ_FLAG_HIDDEN);
    }
}

static uint32_t pack_rand(uint32_t minv, uint32_t maxv) {
    sPackRng = 1664525u * sPackRng + 1013904223u;
    return minv + (sPackRng % (maxv - minv + 1));
}

static void pack_reward() {
    uint32_t delta = pack_rand(1000, 1500);
    sPackTokens += delta;
    sPackSaveAt = millis() + 1800;
    pack_draw_total();
    if (sPackPlus) {
        char b[16];
        char n[12];
        format_tokens(delta, n, sizeof(n));
        snprintf(b, sizeof(b), "+%s", n);
        lv_label_set_text(sPackPlus, b);
        lv_obj_clear_flag(sPackPlus, LV_OBJ_FLAG_HIDDEN);
        sPackPlusUntil = millis() + 320;
    }
}

static const uint8_t kPackF[] = {1, 2, 3, 0};
static const uint16_t kPackMs[] = {220, 200, 280, 160};
static const int16_t kPackKnockAt[] = {-1, 35, -1, -1};
static const uint8_t kPackReward[] = {0, 0, 1, 0};
static const int kPackSteps = 4;

static void pack_enter(uint8_t step, uint32_t now) {
    sPackStep = step;
    sPackStepAt = now;
    sPackKnocked = false;
    pack_show(kPackF[step]);
    if (kPackReward[step]) pack_reward();
    if (kPackKnockAt[step] == 0) {
        sPackKnocked = true;
        beep_request(BEEP_WOOD);
    }
}

static void pack_start_cycle(uint32_t now) {
    sPackBusy = true;
    pack_enter(0, now);
}

void ui_pack_press() {
    uint32_t now = millis();
    if (sPackBusy) {
        if (sPackPending < 8) sPackPending++;
        pack_draw_queue();
        return;
    }
    pack_start_cycle(now);
}

static void pack_reset() {
    sPackTokens = 0;
    sPackPending = 0;
    sPackBusy = false;
    sPackStep = 0;
    sPackKnocked = false;
    sPackSaveAt = millis() + 200;
    pack_show(0);
    pack_draw_total();
    pack_draw_queue();
    if (sPackPlus) lv_obj_add_flag(sPackPlus, LV_OBJ_FLAG_HIDDEN);
    beep_request(BEEP_STOP);
}

static void pack_tick() {
    if (sPackPlusUntil && millis() >= sPackPlusUntil) {
        sPackPlusUntil = 0;
        if (sPackPlus) lv_obj_add_flag(sPackPlus, LV_OBJ_FLAG_HIDDEN);
    }
    if (!sPackBusy) return;
    uint32_t now = millis();
    uint32_t elapsed = now - sPackStepAt;
    int16_t knockAt = kPackKnockAt[sPackStep];
    if (knockAt >= 0 && !sPackKnocked && elapsed >= (uint32_t)knockAt) {
        sPackKnocked = true;
        beep_request(BEEP_WOOD);
    }
    if (elapsed < kPackMs[sPackStep]) return;
    if (sPackStep + 1 >= kPackSteps) {
        sPackBusy = false;
        pack_show(0);
        if (sPackPending > 0) {
            sPackPending--;
            pack_draw_queue();
            pack_start_cycle(now);
        }
        return;
    }
    pack_enter((uint8_t)(sPackStep + 1), now);
}

static void on_pack_click(lv_event_t *e) {
    if (lv_event_get_code(e) != LV_EVENT_CLICKED) return;
    if (sPackDidReset) {
        sPackDidReset = false;
        return;
    }
    if (sSwipeAbs > 28) return;
    ui_pack_press();
}

static int clamp100(int v) {
    if (v < 0) return 0;
    if (v > 100) return 100;
    return v;
}

static int bigger(int a, int b) { return a > b ? a : b; }

static int win_used(bool has, int v) { return has ? clamp100(v) : -1; }

static int bigger_has(int a, int b) {
    if (a < 0) return b;
    if (b < 0) return a;
    return bigger(a, b);
}

static int active_count() {
    int n = 0;
    for (int i = 0; i < LOGO_COUNT; i++) if (sOn[i]) n++;
    return n;
}

static int active_at(int slot) {
    int n = 0;
    for (int i = 0; i < LOGO_COUNT; i++) {
        if (!sOn[i]) continue;
        if (n == slot) return i;
        n++;
    }
    return -1;
}

static int usage_pages() {
    int n = active_count();
    if (n <= 0) return 1;
    return (n + 3) / 4;
}

static int used_max() {
    int m = 0;
    for (int i = 0; i < LOGO_COUNT; i++) {
        if (!sOn[i]) continue;
        int u = 100 - clamp100(sRemain[i]);
        if (u > m) m = u;
    }
    return m;
}

static void fmt_reset(uint32_t sec, char *out, size_t cap) {
    if (sec > 10u * 86400u) sec = 10u * 86400u;
    unsigned d = sec / 86400;
    unsigned h = (sec % 86400) / 3600;
    unsigned m = (sec % 3600) / 60;
    unsigned s = sec % 60;
    if (d) snprintf(out, cap, "%ud %02u:%02u:%02u", d, h, m, s);
    else if (h) snprintf(out, cap, "%uh %02u:%02u", h, m, s);
    else if (m) snprintf(out, cap, "%um %02us", m, s);
    else snprintf(out, cap, "%us", s);
}

static void fmt_cd(uint32_t sec, char *out, size_t cap) {
    if (!sec) {
        snprintf(out, cap, "--");
        return;
    }
    if (sec > 10u * 86400u) sec = 10u * 86400u;
    unsigned d = sec / 86400;
    unsigned h = (sec % 86400) / 3600;
    unsigned m = (sec % 3600) / 60;
    unsigned s = sec % 60;
    if (d) snprintf(out, cap, "%ud %uh", d, h);
    else if (h) snprintf(out, cap, "%uh %02um", h, m);
    else if (m) snprintf(out, cap, "%um %02us", m, s);
    else snprintf(out, cap, "%us", s);
}

static void fmt_tok(int n, char *out, size_t cap) {
    if (n < 0) {
        snprintf(out, cap, "-");
        return;
    }
    if (n == 0) {
        snprintf(out, cap, "0");
        return;
    }
    static const char *u[] = {"", "k", "M", "B", "T"};
    double v = (double)n;
    int i = 0;
    while (v >= 1000.0 && i < 4) {
        v /= 1000.0;
        i++;
    }
    if (v >= 100.0 || (v - (int)v) < 0.05) snprintf(out, cap, "%d%s", (int)(v + 0.5), u[i]);
    else snprintf(out, cap, "%.1f%s", v, u[i]);
}

static bool brand_tracked(const char *id) {
    return !strcmp(id, "codex") || !strcmp(id, "claude") || !strcmp(id, "cursor")
        || !strcmp(id, "glm") || !strcmp(id, "kimi")
        || !strcmp(id, "trae") || !strcmp(id, "coze");
}

static uint32_t remain_from_unix(uint32_t ts) {
    if (!ts) return 0;
    if (ts <= 10u * 86400u) return ts;
    time_t now = time(nullptr);
    if (now > 1700000000 && (time_t)ts > now) {
        uint32_t d = (uint32_t)((time_t)ts - now);
        if (d > 10u * 86400u) d = 10u * 86400u;
        return d;
    }
    return 0;
}

static void apply_live(int i, int remain_used, int h5, int d7, int d30, uint32_t reset_unix) {
    remain_used = clamp100(remain_used);
    sLive[i] = true;
    sRemain[i] = 100 - remain_used;
    sH5[i] = h5 < 0 ? -1 : clamp100(h5);
    sD7[i] = d7 < 0 ? -1 : clamp100(d7);
    sD30[i] = d30 < 0 ? -1 : clamp100(d30);
    sReset[i] = remain_from_unix(reset_unix);
}

static void brand_init() {
    for (int i = 0; i < LOGO_COUNT; i++) {
        sOn[i] = brand_tracked(kBrands[i].id);
        sLive[i] = false;
        sRemain[i] = 100;
        sPrevRemain[i] = -1;
        sReset[i] = 0;
        sH5[i] = -1;
        sD7[i] = -1;
        sD30[i] = -1;
        sTokens[i] = -1;
    }
}

static uint32_t first_reset(uint32_t a, uint32_t b) {
    if (a) return a;
    return b;
}

static void brand_sync_live() {
    for (int i = 0; i < LOGO_COUNT; i++) {
        if (!sOn[i]) continue;
        const char *id = kBrands[i].id;
        sTokens[i] = -1;
        if (!strcmp(id, "cursor") && gStatus.cursor.ok) {
            int a = win_used(gStatus.cursor.has_auto, gStatus.cursor.auto_pct);
            int p = win_used(gStatus.cursor.has_api, gStatus.cursor.api_pct);
            int t = win_used(gStatus.cursor.has_total, gStatus.cursor.total_pct);
            int used = bigger_has(bigger_has(a, p), t);
            if (used < 0) used = 0;
            apply_live(i, used, a, p, t, gStatus.cursor.cycle_end);
        } else if (!strcmp(id, "claude") && gStatus.claude.ok) {
            int h = win_used(gStatus.claude.has_h5, gStatus.claude.h5);
            int d = win_used(gStatus.claude.has_d7, gStatus.claude.d7);
            int used = bigger_has(h, d);
            if (used < 0) {
                long cents = gStatus.claude.daily_tokens;
                used = cents > 0 ? 0 : 100;
                apply_live(i, used, -1, -1, -1, 0);
                sTokens[i] = cents < 0 ? 0 : cents;
            } else {
                apply_live(i, used, h, d, -1, first_reset(gStatus.claude.reset_h5, gStatus.claude.reset_d7));
            }
        } else if (!strcmp(id, "codex") && gStatus.codex.ok) {
            int h = win_used(gStatus.codex.has_h5, gStatus.codex.h5);
            int d = win_used(gStatus.codex.has_d7, gStatus.codex.d7);
            int used = bigger_has(h, d);
            if (used < 0) used = 0;
            apply_live(i, used, h, d, -1, first_reset(gStatus.codex.reset_h5, gStatus.codex.reset_d7));
        } else if (!strcmp(id, "glm") && gStatus.glm.ok) {
            int u5 = gStatus.glm.has_h5 ? (100 - clamp100(gStatus.glm.h5)) : -1;
            int u7 = gStatus.glm.has_d7 ? (100 - clamp100(gStatus.glm.d7)) : -1;
            int um = gStatus.glm.has_mcp ? (100 - clamp100(gStatus.glm.mcp)) : -1;
            int used = bigger_has(bigger_has(u5, u7), um);
            if (used < 0) used = 0;
            apply_live(i, used, u5, u7, um, first_reset(gStatus.glm.reset_h5, gStatus.glm.reset_d7));
            if (gStatus.glm.daily_tokens > 0) sTokens[i] = (int)gStatus.glm.daily_tokens;
        } else if (!strcmp(id, "kimi") && gStatus.kimi.ok) {
            int h = win_used(gStatus.kimi.has_h5, gStatus.kimi.h5);
            int d = win_used(gStatus.kimi.has_d7, gStatus.kimi.d7);
            int used = bigger_has(h, d);
            if (used < 0) used = 0;
            apply_live(i, used, h, d, -1, first_reset(gStatus.kimi.reset_h5, gStatus.kimi.reset_d7));
        } else if (!strcmp(id, "trae") && gStatus.trae.ok) {
            int h = win_used(gStatus.trae.has_h5, gStatus.trae.h5);
            int d = win_used(gStatus.trae.has_d7, gStatus.trae.d7);
            int used = bigger_has(h, d);
            if (used < 0) used = 0;
            apply_live(i, used, h, d, -1, first_reset(gStatus.trae.reset_h5, gStatus.trae.reset_d7));
        } else if (!strcmp(id, "coze") && gStatus.coze.ok) {
            int h = win_used(gStatus.coze.has_h5, gStatus.coze.h5);
            int d = win_used(gStatus.coze.has_d7, gStatus.coze.d7);
            int used = bigger_has(h, d);
            if (used < 0) used = 0;
            apply_live(i, used, h, d, -1, first_reset(gStatus.coze.reset_h5, gStatus.coze.reset_d7));
        }
        if (sLive[i] && sRemain[i] != sPrevRemain[i]) {
            Serial.printf("[LOGO] %s remain=%d used=%d\n", id, sRemain[i], 100 - sRemain[i]);
            sPrevRemain[i] = sRemain[i];
        }
    }
}

static void on_sync(lv_event_t *e) {
    if (lv_event_get_code(e) != LV_EVENT_CLICKED) return;
    ui_toast("SYNC");
    net_poll_now(true);
}

static void on_talk(lv_event_t *e) {
    if (lv_event_get_code(e) != LV_EVENT_CLICKED) return;
    if (sSwipeAbs > 28) return;
    if (voice_is_recording()) {
        voice_stop_and_send();
        beep_click();
    } else if (!voice_is_busy()) {
        beep_click();
        if (sPage != PAGE_DESK) {
            sPage = PAGE_DESK;
            show_current();
        }
        voice_start(VOICE_SRC_TAP);
    }
}

static void on_boot_key(lv_event_t *e) {
    if (lv_event_get_code(e) != LV_EVENT_CLICKED) return;
    if (sSwipeAbs > 28) return;
    if (voice_is_recording()) return;
    beep_click();
    strncpy(gStatus.agent_state, "working", sizeof(gStatus.agent_state) - 1);
    hid_tap_enter();
    ui_toast("ENTER");
}

static void on_stop(lv_event_t *e) {
    if (lv_event_get_code(e) != LV_EVENT_CLICKED) return;
    if (sSwipeAbs > 28) return;
    if (voice_is_recording()) {
        voice_cancel();
        beep_click();
        ui_toast("CANCEL");
        return;
    }
    beep_click();
    hid_tap_esc();
    strncpy(gStatus.agent_state, "idle", sizeof(gStatus.agent_state) - 1);
    ui_toast("STOP");
}

static void on_plan_back(lv_event_t *e) {
    if (lv_event_get_code(e) != LV_EVENT_CLICKED) return;
    sPage = PAGE_USAGE;
    sPlanIdx = -1;
    show_current();
}

static void on_idle_click(lv_event_t *e) {
    lv_event_code_t code = lv_event_get_code(e);
    if (code != LV_EVENT_CLICKED && code != LV_EVENT_PRESSED) return;
    wake_idle();
}

static void on_cell(lv_event_t *e) {
    if (lv_event_get_code(e) != LV_EVENT_CLICKED) return;
    if (sSwipeAbs > 28) return;
    int slot = (int)(intptr_t)lv_event_get_user_data(e);
    int idx = active_at(sUsagePage * 4 + slot);
    if (idx < 0) return;
    sPlanIdx = idx;
    sPage = PAGE_PLAN;
    show_current();
}

static void on_pager_prev(lv_event_t *e) {
    if (lv_event_get_code(e) != LV_EVENT_CLICKED) return;
    ui_prev_page();
}

static void on_pager_next(lv_event_t *e) {
    if (lv_event_get_code(e) != LV_EVENT_CLICKED) return;
    ui_next_page();
}

static void quota_chime() {
    int used = used_max();
    if (used < gAlertThreshold) gAlertAck = false;
    if (used < gWarnThreshold) gWarnAck = false;
    if (voice_is_recording() || voice_is_busy()) return;
    if (used >= gAlertThreshold) {
        if (!gAlertAck) {
            gAlertAck = true;
            beep_request(BEEP_ALERT);
            ui_toast("HOT");
        }
        return;
    }
    if (used >= gWarnThreshold && !gWarnAck) {
        gWarnAck = true;
        beep_request(BEEP_WARN);
    }
}

void ui_toast(const char *msg) {
    sHintUntil = millis() + 1400;
    strncpy(sFlash, msg ? msg : "", sizeof(sFlash) - 1);
    sFlash[sizeof(sFlash) - 1] = 0;
    if (sToast && sFlash[0]) {
        lv_label_set_text(sToast, sFlash);
        lv_obj_clear_flag(sToast, LV_OBJ_FLAG_HIDDEN);
    }
}

static void wake_idle() {
    sActAt = millis();
    if (sPage != PAGE_IDLE) return;
    sPage = PAGE_DESK;
    display_swallow_until_release();
    show_current();
    ui_refresh_from_status();
}

void ui_note_activity() {
    sActAt = millis();
    if (sPage == PAGE_IDLE) wake_idle();
}

static void bubble_tree(lv_obj_t *obj) {
    uint32_t n = lv_obj_get_child_cnt(obj);
    for (uint32_t i = 0; i < n; i++) {
        lv_obj_t *c = lv_obj_get_child(obj, i);
        lv_obj_clear_flag(c, LV_OBJ_FLAG_SCROLLABLE);
        if (lv_obj_has_flag(c, LV_OBJ_FLAG_CLICKABLE)) {
            lv_obj_clear_flag(c, LV_OBJ_FLAG_EVENT_BUBBLE);
            continue;
        }
        lv_obj_add_flag(c, LV_OBJ_FLAG_EVENT_BUBBLE);
        bubble_tree(c);
    }
}

static void on_swipe(lv_event_t *e) {
    lv_indev_t *indev = lv_indev_get_act();
    if (!indev) return;
    lv_event_code_t code = lv_event_get_code(e);
    if (code == LV_EVENT_GESTURE) {
        if (ui_nav_blocked()) return;
        lv_dir_t dir = lv_indev_get_gesture_dir(indev);
        if (sPage == PAGE_IDLE) {
            wake_idle();
            lv_indev_wait_release(indev);
            return;
        }
        if (sPage == PAGE_PLAN) {
            sPage = PAGE_USAGE;
            show_current();
            lv_indev_wait_release(indev);
            return;
        }
        if (dir == LV_DIR_LEFT) ui_next_page();
        else if (dir == LV_DIR_RIGHT) ui_prev_page();
        lv_indev_wait_release(indev);
        sSwipeX = -1;
        return;
    }
    lv_point_t p;
    lv_indev_get_point(indev, &p);
    if (code == LV_EVENT_PRESSED) {
        sIdlePress = (sPage == PAGE_IDLE);
        if (sIdlePress) wake_idle();
        else ui_note_activity();
        sSwipeX = p.x;
        sSwipeY = p.y;
        sSwipeAbs = 0;
        if (sPage == PAGE_PACK) {
            sPackHold = millis();
            sPackDidReset = false;
        }
    }
    if (code == LV_EVENT_RELEASED && sSwipeX >= 0) {
        int dx = p.x - sSwipeX;
        int dy = p.y - sSwipeY;
        int adx = dx < 0 ? -dx : dx;
        int ady = dy < 0 ? -dy : dy;
        sSwipeAbs = adx > ady ? adx : ady;
        uint32_t held = sPackHold ? (millis() - sPackHold) : 0;
        sSwipeX = -1;
        sSwipeY = -1;
        if (sIdlePress) {
            sIdlePress = false;
            sPackHold = 0;
            return;
        }
        if (ui_nav_blocked()) {
            sPackHold = 0;
            return;
        }
        if (sPage == PAGE_PLAN) {
            if (sSwipeAbs > 32) {
                sPage = PAGE_USAGE;
                show_current();
            }
            sPackHold = 0;
            return;
        }
        if (sPage == PAGE_PACK && held >= 1400 && sSwipeAbs < 20) {
            pack_reset();
            sPackDidReset = true;
            sPackHold = 0;
            return;
        }
        if (sPage == PAGE_PACK && sSwipeAbs < 40 && held < 1400) {
            ui_pack_press();
            sPackDidReset = true;
            sPackHold = 0;
            return;
        }
        sPackHold = 0;
        if (sPage == PAGE_USAGE && ady > 40 && ady > adx) {
            if (dy < 0) ui_next_page();
            else ui_prev_page();
            return;
        }
        if (dx < -40) ui_next_page();
        else if (dx > 40) ui_prev_page();
    }
}

static void cell_geom(int n, int i, int *x, int *y, int *s) {
    /* 3-up uses the same 2x2 grid as 4-up (zoom 256). The old triangle used 60px
       marks (zoom 274); dense alpha frames like Coze blanked that page. */
    if (n == 3) n = 4;
    static const int mark_s[] = {0, 92, 72, 60, 56};
    *s = mark_s[n];
    if (n == 1) {
        *x = 74;
        *y = 70;
    } else if (n == 2) {
        *x = 34 + i * 100;
        *y = 80;
    } else {
        *x = 36 + (i % 2) * 114;
        *y = 56 + (i / 2) * 74;
    }
}

static void paint_logo_fill(lv_obj_t *mark, lv_obj_t *gray, lv_obj_t *clip, lv_obj_t *color,
                           int idx, int box, int remain, bool live) {
    lv_obj_clear_flag(mark, LV_OBJ_FLAG_OVERFLOW_VISIBLE);
    lv_obj_clear_flag(clip, LV_OBJ_FLAG_OVERFLOW_VISIBLE);
    lv_obj_set_size(mark, box, box);
    uint16_t zoom = (uint16_t)(box * 256 / LOGO_SIZE);
    if (zoom < 1) zoom = 1;
    int vis = live ? clamp100(remain) : 0;
    int clip_h = vis <= 0 ? 0 : (box * vis + 99) / 100;
    if (vis > 0 && clip_h < 2) clip_h = 2;

    lv_img_set_src(gray, &logo_img[idx]);
    lv_img_set_src(color, &logo_img[idx]);
    lv_img_set_zoom(gray, zoom);
    lv_img_set_zoom(color, zoom);
    lv_img_set_pivot(gray, 0, 0);
    lv_img_set_pivot(color, 0, 0);
    lv_img_set_antialias(gray, true);
    lv_img_set_antialias(color, true);
    lv_obj_set_size(gray, box, box);
    lv_obj_set_pos(gray, 0, 0);
    lv_obj_set_style_img_recolor(gray, C_GRAY, 0);
    lv_obj_set_style_img_recolor_opa(gray, LV_OPA_COVER, 0);

    if (clip_h <= 0) {
        lv_obj_add_flag(clip, LV_OBJ_FLAG_HIDDEN);
    } else {
        lv_obj_clear_flag(clip, LV_OBJ_FLAG_HIDDEN);
        lv_obj_set_size(clip, box, clip_h);
        lv_obj_align(clip, LV_ALIGN_BOTTOM_MID, 0, 0);
        lv_obj_set_size(color, box, box);
        lv_obj_set_pos(color, 0, clip_h - box);
        lv_obj_set_style_img_recolor_opa(color, LV_OPA_TRANSP, 0);
    }
    lv_obj_invalidate(mark);
}

static void usage_paint() {
    int total = usage_pages();
    if (sUsagePage >= total) sUsagePage = total - 1;
    if (sUsagePage < 0) sUsagePage = 0;
    int n = active_count();
    int start = sUsagePage * 4;
    int slice = n - start;
    if (slice > 4) slice = 4;
    if (slice < 0) slice = 0;

    if (sPager) {
        if (total > 1) {
            lv_obj_clear_flag(sPager, LV_OBJ_FLAG_HIDDEN);
            if (sPagerNum) {
                char b[16];
                snprintf(b, sizeof(b), "%d/%d", sUsagePage + 1, total);
                lv_label_set_text(sPagerNum, b);
            }
        } else {
            lv_obj_add_flag(sPager, LV_OBJ_FLAG_HIDDEN);
        }
    }

    for (int i = 0; i < 4; i++) {
        if (!sCell[i]) continue;
        if (i >= slice) {
            lv_obj_add_flag(sCell[i], LV_OBJ_FLAG_HIDDEN);
            continue;
        }
        int idx = active_at(start + i);
        if (idx < 0) {
            lv_obj_add_flag(sCell[i], LV_OBJ_FLAG_HIDDEN);
            continue;
        }
        int x, y, s;
        cell_geom(slice, i, &x, &y, &s);
        int remain = clamp100(sRemain[idx]);
        lv_obj_clear_flag(sCell[i], LV_OBJ_FLAG_HIDDEN);
        lv_obj_set_pos(sCell[i], x, y);
        lv_obj_set_size(sCell[i], s, s + 16);
        lv_obj_align(sMark[i], LV_ALIGN_TOP_MID, 0, 0);
        paint_logo_fill(sMark[i], sGray[i], sClip[i], sColor[i], idx, s, remain, sLive[idx]);

        char cd[16];
        if (!sLive[idx]) snprintf(cd, sizeof(cd), "--");
        else fmt_cd(sReset[idx], cd, sizeof(cd));
        lv_label_set_text(sCd[i], cd);
        lv_color_t cc = C_MUTE;
        if (sLive[idx] && sReset[idx] && sReset[idx] < 600) cc = C_HOT;
        else if (sLive[idx] && sReset[idx] && sReset[idx] < 3600) cc = C_GOLD;
        lv_obj_set_style_text_color(sCd[i], cc, 0);
        lv_obj_align(sCd[i], LV_ALIGN_BOTTOM_MID, 0, 0);
    }
}

static void idle_paint() {
    time_t now = time(nullptr);
    struct tm tmv;
    struct tm *tmp = (now > 1700000000) ? localtime(&now) : nullptr;
    bool ok = tmp != nullptr;
    if (ok) tmv = *tmp;
    static const char *wk[] = {"日", "一", "二", "三", "四", "五", "六"};
    char b[32];
    if (ok) {
        snprintf(b, sizeof(b), "%02d:%02d", tmv.tm_hour, tmv.tm_min);
        lv_label_set_text(sIdleTime, b);
        snprintf(b, sizeof(b), "%d / %d    周%s", tmv.tm_mon + 1, tmv.tm_mday, wk[tmv.tm_wday]);
        lv_label_set_text(sIdleDate, b);
    } else {
        lv_label_set_text(sIdleTime, "--:--");
        lv_label_set_text(sIdleDate, "-- / --");
    }
    lv_obj_align(sIdleTime, LV_ALIGN_CENTER, 0, -12);
    lv_obj_align(sIdleDate, LV_ALIGN_CENTER, 0, 38);
    paint_one_bat(sIdleBat, sIdleBatIcon, sIdleBatNub, sIdleBatFill, C_GRAY);
}

static void plan_paint() {
    if (sPlanIdx < 0 || sPlanIdx >= LOGO_COUNT) return;
    const BrandMeta &b = kBrands[sPlanIdx];
    const char *id = b.id;
    lv_color_t col = lv_color_hex(b.color);
    if (!strcmp(id, "claude") && sLive[sPlanIdx] && sH5[sPlanIdx] < 0 && sD7[sPlanIdx] < 0 && sTokens[sPlanIdx] >= 0)
        lv_label_set_text(sPlanName, "DEEPSEEK");
    else
        lv_label_set_text(sPlanName, b.name);
    if (lv_obj_get_child_cnt(sPlanBack) > 0)
        lv_obj_set_style_text_color(lv_obj_get_child(sPlanBack, 0), col, 0);

    char u[32];
    time_t ts = (time_t)gStatus.ts;
    struct tm *tmp = (sLive[sPlanIdx] && ts > 1700000000) ? localtime(&ts) : nullptr;
    if (tmp) snprintf(u, sizeof(u), "UPD  %02d:%02d", tmp->tm_hour, tmp->tm_min);
    else snprintf(u, sizeof(u), "UPD  --");
    lv_label_set_text(sPlanUpd, u);

    lv_img_set_src(sPlanGhost, &logo_img[sPlanIdx]);
    lv_img_set_zoom(sPlanGhost, 540);
    lv_img_set_pivot(sPlanGhost, 0, 0);
    lv_obj_set_style_img_opa(sPlanGhost, 33, 0);
    if (b.flags & BR_MONO) {
        lv_obj_set_style_img_recolor(sPlanGhost, C_INK, 0);
        lv_obj_set_style_img_recolor_opa(sPlanGhost, LV_OPA_70, 0);
    } else {
        lv_obj_set_style_img_recolor_opa(sPlanGhost, LV_OPA_TRANSP, 0);
    }

    const char *labs[3] = {"5H", "7D", "30D"};
    if (!strcmp(id, "cursor")) {
        labs[0] = "AUTO";
        labs[1] = "API";
        labs[2] = "ALL";
    } else if (!strcmp(id, "glm")) {
        labs[2] = "MCP";
    } else if (!strcmp(id, "trae")) {
        labs[0] = "CRED";
    } else if (!strcmp(id, "coze")) {
        labs[0] = "TOOL";
    }
    int usedv[3] = {sH5[sPlanIdx], sD7[sPlanIdx], sD30[sPlanIdx]};
    for (int i = 0; i < 3; i++) {
        lv_label_set_text(sPlanLab[i], labs[i]);
        bool show = sLive[sPlanIdx] ? usedv[i] >= 0 : (i < 2 || !strcmp(id, "cursor") || !strcmp(id, "glm"));
        if (!show) {
            lv_obj_add_flag(sPlanLab[i], LV_OBJ_FLAG_HIDDEN);
            lv_obj_add_flag(sPlanPct[i], LV_OBJ_FLAG_HIDDEN);
            if (sPlanTrack[i]) lv_obj_add_flag(sPlanTrack[i], LV_OBJ_FLAG_HIDDEN);
            continue;
        }
        lv_obj_clear_flag(sPlanLab[i], LV_OBJ_FLAG_HIDDEN);
        lv_obj_clear_flag(sPlanPct[i], LV_OBJ_FLAG_HIDDEN);
        if (sPlanTrack[i]) lv_obj_clear_flag(sPlanTrack[i], LV_OBJ_FLAG_HIDDEN);
        int remain = (sLive[sPlanIdx] && usedv[i] >= 0) ? (100 - clamp100(usedv[i])) : -1;
        char p[16];
        const ProviderQuota *qty = nullptr;
        if (!strcmp(id, "trae")) qty = &gStatus.trae;
        else if (!strcmp(id, "coze")) qty = &gStatus.coze;
        if (remain < 0) snprintf(p, sizeof(p), "--");
        else if (i == 0 && qty && qty->has_qty && qty->cap > 0)
            snprintf(p, sizeof(p), "%d/%d", qty->left < 0 ? 0 : qty->left, qty->cap);
        else snprintf(p, sizeof(p), "%d%%", remain);
        lv_label_set_text(sPlanPct[i], p);
        lv_color_t pc = C_MUTE;
        if (remain >= 0 && remain <= 10) pc = C_HOT;
        else if (remain >= 0 && remain <= 30) pc = C_GOLD;
        else if (remain >= 0) pc = col;
        lv_obj_set_style_text_color(sPlanPct[i], pc, 0);
        int w = remain < 0 ? 0 : (208 * remain) / 100;
        lv_obj_set_width(sPlanFill[i], w);
        lv_obj_set_style_bg_color(sPlanFill[i], remain < 0 ? C_MUTE : col, 0);
    }

    char foot[40];
    foot[0] = 0;
    if (sLive[sPlanIdx] && sReset[sPlanIdx]) {
        char rs[24];
        fmt_reset(sReset[sPlanIdx], rs, sizeof(rs));
        snprintf(foot, sizeof(foot), "RESET  %s", rs);
    } else if (sLive[sPlanIdx] && !strcmp(id, "claude") && sH5[sPlanIdx] < 0 && sD7[sPlanIdx] < 0 && sTokens[sPlanIdx] >= 0) {
        long n = sTokens[sPlanIdx];
        snprintf(foot, sizeof(foot), "YUAN  %ld.%02ld", n / 100, n % 100);
    } else if (sLive[sPlanIdx] && sTokens[sPlanIdx] > 0) {
        char tok[12];
        fmt_tok(sTokens[sPlanIdx], tok, sizeof(tok));
        snprintf(foot, sizeof(foot), "TODAY  %s  TOK", tok);
    }
    lv_label_set_text(sPlanFoot, foot);
    lv_obj_set_style_text_color(sPlanFoot, C_MUTE, 0);
}

static void show_current() {
    lv_scr_load(sScreens[sPage]);
    if (sLamp) {
        if (sPage == PAGE_DESK) lv_obj_clear_flag(sLamp, LV_OBJ_FLAG_HIDDEN);
        else lv_obj_add_flag(sLamp, LV_OBJ_FLAG_HIDDEN);
    }
    if (sPage == PAGE_PACK) pack_show(sPackFrame);
    if (sPage == PAGE_USAGE) usage_paint();
    if (sPage == PAGE_IDLE) idle_paint();
    if (sPage == PAGE_PLAN) plan_paint();
}

static void make_desk(lv_obj_t *scr) {
    make_rect(scr, 4, 240, C_COPPER);
    sDeskBar = make_rect(scr, 240, 4, C_HOT);
    lv_obj_add_flag(sDeskBar, LV_OBJ_FLAG_HIDDEN);

    /* Caps L→R facing screen: 发送 | 取消 | 讲话. */
    static const int kx[3] = {0, 85, 170};
    static const char *ka[3] = {"发送", "取消", "讲话"};
    lv_event_cb_t kcb[3] = {on_boot_key, on_stop, on_talk};
    for (int i = 0; i < 3; i++) {
        sKey[i] = make_hit(scr, 70, 36, C_ORANGE, kcb[i]);
        lv_obj_set_style_radius(sKey[i], 10, LV_PART_MAIN);
        lv_obj_set_style_clip_corner(sKey[i], true, LV_PART_MAIN);
        lv_obj_set_pos(sKey[i], kx[i], 8);
        sKeyAct[i] = lv_label_create(sKey[i]);
        lv_label_set_text(sKeyAct[i], ka[i]);
        lv_obj_set_style_text_font(sKeyAct[i], &font_idle_16, 0);
        lv_obj_set_style_text_color(sKeyAct[i], C_WHITE, 0);
        lv_obj_center(sKeyAct[i]);
    }

    /* Rec timer — only visible while recording. */
    sLine = make_label(scr, &lv_font_montserrat_28, C_INK);
    lv_label_set_text(sLine, "");
    lv_obj_set_width(sLine, 200);
    lv_obj_set_style_text_align(sLine, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_align(sLine, LV_ALIGN_TOP_MID, 0, 58);
    lv_obj_add_flag(sLine, LV_OBJ_FLAG_HIDDEN);

    /* Soft pulse halo behind mic (shown while recording). */
    sTalkHalo = make_rect(scr, 116, 116, C_ORANGE);
    lv_obj_set_style_radius(sTalkHalo, 58, 0);
    lv_obj_set_style_bg_opa(sTalkHalo, LV_OPA_30, 0);
    lv_obj_set_pos(sTalkHalo, 18, 108);
    lv_obj_add_flag(sTalkHalo, LV_OBJ_FLAG_HIDDEN);

    sTalkBtn = make_hit(scr, 100, 100, C_ORANGE, on_talk);
    lv_obj_set_style_radius(sTalkBtn, 50, LV_PART_MAIN);
    lv_obj_set_style_clip_corner(sTalkBtn, true, LV_PART_MAIN);
    lv_obj_set_pos(sTalkBtn, 26, 116);
    sTalkLab = lv_label_create(sTalkBtn);
    lv_label_set_text(sTalkLab, ICON_MIC);
    lv_obj_set_style_text_font(sTalkLab, &font_icons, 0);
    lv_obj_set_style_text_color(sTalkLab, C_WHITE, 0);
    lv_obj_center(sTalkLab);

    sStopBtn = make_hit(scr, 100, 100, C_WELL, on_stop);
    lv_obj_set_style_radius(sStopBtn, 50, LV_PART_MAIN);
    lv_obj_set_style_clip_corner(sStopBtn, true, LV_PART_MAIN);
    lv_obj_set_pos(sStopBtn, 134, 116);
    sStopLab = lv_label_create(sStopBtn);
    lv_label_set_text(sStopLab, ICON_BAN);
    lv_obj_set_style_text_font(sStopLab, &font_icons, 0);
    lv_obj_set_style_text_color(sStopLab, C_MUTE, 0);
    lv_obj_center(sStopLab);

    for (int i = 0; i < 2; i++) {
        sDots[i] = make_rect(scr, i == 0 ? 12 : 5, 4, i == 0 ? C_COPPER : C_WELL);
        lv_obj_set_style_radius(sDots[i], 2, 0);
        lv_obj_align(sDots[i], LV_ALIGN_BOTTOM_MID, (int)((i - 0.5f) * 16), -8);
    }
}

static void make_usage(lv_obj_t *scr) {
    make_rect(scr, 4, 240, C_HOT);
    lv_obj_t *k = make_label(scr, &lv_font_montserrat_12, C_MUTE);
    lv_label_set_text(k, "PLAN");
    lv_obj_align(k, LV_ALIGN_TOP_LEFT, 18, 12);
    lv_obj_t *t = make_label(scr, &lv_font_montserrat_20, C_INK);
    lv_label_set_text(t, "USAGE");
    lv_obj_align(t, LV_ALIGN_TOP_LEFT, 18, 26);

    lv_obj_t *sync = make_hit(scr, 56, 28, C_BG, on_sync);
    lv_obj_align(sync, LV_ALIGN_TOP_RIGHT, -10, 18);
    lv_obj_t *sl = lv_label_create(sync);
    lv_label_set_text(sl, "SYNC");
    lv_obj_set_style_text_font(sl, &lv_font_montserrat_12, 0);
    lv_obj_set_style_text_color(sl, C_MUTE, 0);
    lv_obj_center(sl);

    for (int i = 0; i < 4; i++) {
        sCell[i] = make_hit(scr, 56, 72, C_BG, nullptr);
        lv_obj_add_event_cb(sCell[i], on_cell, LV_EVENT_CLICKED, (void *)(intptr_t)i);
        lv_obj_set_style_bg_opa(sCell[i], LV_OPA_TRANSP, 0);
        sMark[i] = make_rect(sCell[i], 56, 56, C_BG);
        lv_obj_set_style_bg_opa(sMark[i], LV_OPA_TRANSP, 0);
        sGray[i] = lv_img_create(sMark[i]);
        lv_obj_clear_flag(sGray[i], LV_OBJ_FLAG_CLICKABLE);
        sClip[i] = make_rect(sMark[i], 56, 56, C_BG);
        lv_obj_set_style_bg_opa(sClip[i], LV_OPA_TRANSP, 0);
        lv_obj_clear_flag(sClip[i], LV_OBJ_FLAG_CLICKABLE);
        sColor[i] = lv_img_create(sClip[i]);
        lv_obj_clear_flag(sColor[i], LV_OBJ_FLAG_CLICKABLE);
        sCd[i] = make_label(sCell[i], &lv_font_montserrat_12, C_MUTE);
        lv_label_set_text(sCd[i], "");
    }

    sPager = lv_obj_create(scr);
    lv_obj_remove_style_all(sPager);
    lv_obj_set_size(sPager, 240, 32);
    lv_obj_align(sPager, LV_ALIGN_BOTTOM_MID, 0, 0);
    lv_obj_clear_flag(sPager, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_add_flag(sPager, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_clear_flag(sPager, LV_OBJ_FLAG_EVENT_BUBBLE);

    lv_obj_t *prev = make_hit(sPager, 36, 32, C_BG, on_pager_prev);
    lv_obj_align(prev, LV_ALIGN_LEFT_MID, 40, 0);
    lv_obj_set_style_bg_opa(prev, LV_OPA_TRANSP, 0);
    lv_obj_t *pl = lv_label_create(prev);
    lv_label_set_text(pl, "<");
    lv_obj_set_style_text_font(pl, &lv_font_montserrat_20, 0);
    lv_obj_set_style_text_color(pl, C_GOLD, 0);
    lv_obj_center(pl);

    sPagerNum = make_label(sPager, &lv_font_montserrat_12, C_MUTE);
    lv_label_set_text(sPagerNum, "1/9");
    lv_obj_center(sPagerNum);

    lv_obj_t *next = make_hit(sPager, 36, 32, C_BG, on_pager_next);
    lv_obj_align(next, LV_ALIGN_RIGHT_MID, -40, 0);
    lv_obj_set_style_bg_opa(next, LV_OPA_TRANSP, 0);
    lv_obj_t *nl = lv_label_create(next);
    lv_label_set_text(nl, ">");
    lv_obj_set_style_text_font(nl, &lv_font_montserrat_20, 0);
    lv_obj_set_style_text_color(nl, C_GOLD, 0);
    lv_obj_center(nl);
}

static void make_idle(lv_obj_t *scr) {
    lv_obj_add_flag(scr, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_add_event_cb(scr, on_idle_click, LV_EVENT_PRESSED, nullptr);
    lv_obj_add_event_cb(scr, on_idle_click, LV_EVENT_CLICKED, nullptr);

    make_bat_row(scr, C_IDLE, &sIdleBatRow, &sIdleBatIcon, &sIdleBatFill, &sIdleBatNub, &sIdleBat);
    lv_obj_set_style_text_font(sIdleBat, &font_idle_16, 0);
    lv_obj_align(sIdleBatRow, LV_ALIGN_TOP_RIGHT, -14, 14);

    sIdleTime = make_label(scr, &font_idle_time, C_TIME);
    lv_obj_set_style_text_letter_space(sIdleTime, 2, 0);
    lv_label_set_text(sIdleTime, "--:--");
    lv_obj_align(sIdleTime, LV_ALIGN_CENTER, 0, -12);

    sIdleDate = make_label(scr, &font_idle_16, C_MUTE);
    lv_obj_set_style_text_letter_space(sIdleDate, 2, 0);
    lv_label_set_text(sIdleDate, "");
    lv_obj_align(sIdleDate, LV_ALIGN_CENTER, 0, 38);

    lv_obj_t *hit = lv_obj_create(scr);
    lv_obj_remove_style_all(hit);
    lv_obj_set_size(hit, 240, 240);
    lv_obj_set_pos(hit, 0, 0);
    lv_obj_set_style_bg_opa(hit, LV_OPA_TRANSP, 0);
    lv_obj_add_flag(hit, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_clear_flag(hit, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_clear_flag(hit, LV_OBJ_FLAG_EVENT_BUBBLE);
    lv_obj_add_event_cb(hit, on_idle_click, LV_EVENT_PRESSED, nullptr);
    lv_obj_add_event_cb(hit, on_idle_click, LV_EVENT_CLICKED, nullptr);
    lv_obj_move_foreground(hit);
}

static void make_plan(lv_obj_t *scr) {
    sPlanGhost = lv_img_create(scr);
    lv_obj_set_size(sPlanGhost, 118, 118);
    lv_obj_align(sPlanGhost, LV_ALIGN_TOP_RIGHT, 8, 52);
    lv_obj_clear_flag(sPlanGhost, LV_OBJ_FLAG_CLICKABLE);

    sPlanBack = make_hit(scr, 36, 36, C_PLAN, on_plan_back);
    lv_obj_set_style_bg_opa(sPlanBack, LV_OPA_TRANSP, 0);
    lv_obj_set_pos(sPlanBack, 6, 8);
    lv_obj_t *bl = lv_label_create(sPlanBack);
    lv_label_set_text(bl, "<");
    lv_obj_set_style_text_font(bl, &lv_font_montserrat_20, 0);
    lv_obj_set_style_text_color(bl, C_COPPER, 0);
    lv_obj_center(bl);

    sPlanName = make_label(scr, &lv_font_montserrat_16, C_INK);
    lv_label_set_text(sPlanName, "");
    lv_obj_align(sPlanName, LV_ALIGN_TOP_LEFT, 42, 12);
    sPlanUpd = make_label(scr, &lv_font_montserrat_12, C_MUTE);
    lv_label_set_text(sPlanUpd, "");
    lv_obj_align(sPlanUpd, LV_ALIGN_TOP_LEFT, 42, 34);

    static const char *labs[3] = {"5H", "7D", "30D"};
    for (int i = 0; i < 3; i++) {
        int y = 70 + i * 40;
        sPlanLab[i] = make_label(scr, &lv_font_montserrat_12, C_MUTE);
        lv_label_set_text(sPlanLab[i], labs[i]);
        lv_obj_align(sPlanLab[i], LV_ALIGN_TOP_LEFT, 16, y);
        sPlanPct[i] = make_label(scr, &lv_font_montserrat_14, C_COPPER);
        lv_label_set_text(sPlanPct[i], "--");
        lv_obj_align(sPlanPct[i], LV_ALIGN_TOP_RIGHT, -16, y);
        sPlanTrack[i] = make_rect(scr, 208, 2, lv_color_hex(0x241F1C));
        lv_obj_align(sPlanTrack[i], LV_ALIGN_TOP_LEFT, 16, y + 20);
        sPlanFill[i] = make_rect(sPlanTrack[i], 0, 2, C_COPPER);
        lv_obj_align(sPlanFill[i], LV_ALIGN_LEFT_MID, 0, 0);
    }
    sPlanFoot = make_label(scr, &lv_font_montserrat_12, C_MUTE);
    lv_label_set_text(sPlanFoot, "");
    lv_obj_align(sPlanFoot, LV_ALIGN_BOTTOM_LEFT, 16, -16);
}

static void make_pack(lv_obj_t *scr) {
    paint_scr(scr, lv_color_hex(0x000000));
    lv_obj_add_flag(scr, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_add_event_cb(scr, on_pack_click, LV_EVENT_CLICKED, nullptr);

    sPackImg = lv_img_create(scr);
    lv_obj_clear_flag(sPackImg, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_align(sPackImg, LV_ALIGN_TOP_LEFT, 0, 0);

    lv_obj_t *bar = make_rect(scr, 240, 28, lv_color_hex(0x000000));
    lv_obj_align(bar, LV_ALIGN_TOP_MID, 0, 10);
    lv_obj_set_flex_flow(bar, LV_FLEX_FLOW_ROW);
    lv_obj_set_flex_align(bar, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER);
    lv_obj_set_style_pad_column(bar, 5, 0);
    lv_obj_move_foreground(bar);

    lv_obj_t *sparkL = make_label(bar, &font_idle_12, C_PACK_SPARK);
    lv_label_set_text(sparkL, "✦");
    lv_obj_t *labSave = make_label(bar, &font_idle_12, C_PACK_LAB);
    lv_label_set_text(labSave, "节省");
    sPackTotal = make_label(bar, &lv_font_montserrat_20, C_PACK_AMT);
    lv_label_set_text(sPackTotal, "0K");
    lv_obj_t *labTok = make_label(bar, &font_idle_12, C_PACK_LAB);
    lv_label_set_text(labTok, "词元");
    lv_obj_t *sparkR = make_label(bar, &font_idle_12, C_PACK_SPARK);
    lv_label_set_text(sparkR, "✦");

    sPackPlus = make_label(scr, &lv_font_montserrat_16, C_PLUS);
    lv_label_set_text(sPackPlus, "");
    lv_obj_add_flag(sPackPlus, LV_OBJ_FLAG_HIDDEN);
    lv_obj_align(sPackPlus, LV_ALIGN_TOP_MID, 0, 38);
    lv_obj_move_foreground(sPackPlus);

    for (int i = 0; i < 8; i++) {
        sPackQueue[i] = make_rect(scr, 5, 14, C_GOLD);
        lv_obj_align(sPackQueue[i], LV_ALIGN_BOTTOM_RIGHT, -14 - (7 - i) * 8, -42);
        lv_obj_add_flag(sPackQueue[i], LV_OBJ_FLAG_HIDDEN);
        lv_obj_move_foreground(sPackQueue[i]);
    }
    pack_draw_total();
}

void ui_init() {
    pack_load();
    brand_init();
    sActAt = millis();
    sResetTickAt = millis();
    lv_disp_t *disp = lv_disp_get_default();
    lv_theme_t *th = lv_theme_default_init(disp, C_COPPER, C_MUTE, true, LV_FONT_DEFAULT);
    lv_disp_set_theme(disp, th);

    lv_color_t bgs[PAGE_COUNT] = {C_BG, C_BG, lv_color_hex(0x000000), C_IDLE, C_PLAN};
    for (int i = 0; i < PAGE_COUNT; i++) {
        sScreens[i] = lv_obj_create(nullptr);
        paint_scr(sScreens[i], bgs[i]);
        lv_obj_add_event_cb(sScreens[i], on_swipe, LV_EVENT_PRESSED, nullptr);
        lv_obj_add_event_cb(sScreens[i], on_swipe, LV_EVENT_RELEASED, nullptr);
        lv_obj_add_event_cb(sScreens[i], on_swipe, LV_EVENT_GESTURE, nullptr);
    }
    make_desk(sScreens[PAGE_DESK]);
    make_usage(sScreens[PAGE_USAGE]);
    make_pack(sScreens[PAGE_PACK]);
    make_idle(sScreens[PAGE_IDLE]);
    make_plan(sScreens[PAGE_PLAN]);
    for (int i = 0; i < PAGE_COUNT; i++) bubble_tree(sScreens[i]);
    lv_obj_add_flag(sScreens[PAGE_PACK], LV_OBJ_FLAG_CLICKABLE);

    sLamp = make_rect(lv_layer_top(), 8, 8, C_LAMP);
    lv_obj_set_style_radius(sLamp, 4, 0);
    lv_obj_align(sLamp, LV_ALIGN_TOP_RIGHT, -10, 10);

    sToast = make_label(lv_layer_top(), &lv_font_montserrat_12, C_GOLD);
    lv_label_set_text(sToast, "");
    lv_obj_set_style_text_align(sToast, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_set_width(sToast, 204);
    lv_obj_align(sToast, LV_ALIGN_TOP_MID, 0, 8);
    lv_obj_add_flag(sToast, LV_OBJ_FLAG_HIDDEN);

    lv_scr_load(sScreens[sPage]);
    pack_draw_total();
    usage_paint();
    ui_refresh_from_status();
}

static bool desk_running() {
    return !strcmp(gStatus.agent_state, "working") || !strcmp(gStatus.agent_state, "waiting");
}

static void paint_lamp() {
    if (!sLamp) return;
    int used = used_max();
    lv_color_t c = C_LAMP;
    if (used >= 90) c = C_HOT;
    else if (voice_is_recording()) c = C_TALK;
    else if (!strcmp(gStatus.agent_state, "working")) c = C_RUN;
    else if (used >= 70) c = C_GOLD;
    lv_obj_set_style_bg_color(sLamp, c, 0);
}

void ui_refresh_from_status() {
    brand_sync_live();
    bool rec = voice_is_recording();
    bool running = desk_running();

    if (sLine) {
        if (rec) {
            uint32_t ms = voice_rec_ms();
            char t[16];
            snprintf(t, sizeof(t), "%u.%u", (unsigned)(ms / 1000), (unsigned)((ms / 100) % 10));
            lv_label_set_text(sLine, t);
            lv_obj_set_style_text_font(sLine, &lv_font_montserrat_28, 0);
            lv_obj_set_style_text_color(sLine, C_INK, 0);
            lv_obj_set_width(sLine, 200);
            lv_obj_set_style_text_align(sLine, LV_TEXT_ALIGN_CENTER, 0);
            lv_obj_align(sLine, LV_ALIGN_TOP_MID, 0, 58);
            lv_obj_clear_flag(sLine, LV_OBJ_FLAG_HIDDEN);
        } else {
            lv_label_set_text(sLine, "");
            lv_obj_add_flag(sLine, LV_OBJ_FLAG_HIDDEN);
        }
    }

    if (sKeyAct[0] && sKeyAct[1] && sKeyAct[2]) {
        static const char *ka[3] = {"发送", "取消", "讲话"};
        for (int i = 0; i < 3; i++) {
            lv_label_set_text(sKeyAct[i], ka[i]);
            lv_obj_set_style_text_color(sKeyAct[i], C_WHITE, 0);
            lv_color_t bg = C_ORANGE;
            if (i == 2 && rec) bg = lv_color_hex(0xC45C12);
            else if (i == 1 && (rec || running)) bg = lv_color_hex(0xC45C12);
            lv_obj_set_style_bg_color(sKey[i], bg, LV_PART_MAIN);
        }
    }

    if (sTalkHalo) {
        if (rec) lv_obj_clear_flag(sTalkHalo, LV_OBJ_FLAG_HIDDEN);
        else {
            lv_obj_add_flag(sTalkHalo, LV_OBJ_FLAG_HIDDEN);
            lv_obj_set_style_bg_opa(sTalkHalo, LV_OPA_30, 0);
        }
    }

    if (sTalkBtn && sTalkLab) {
        lv_label_set_text(sTalkLab, ICON_MIC);
        lv_obj_set_style_text_font(sTalkLab, &font_icons, 0);
        if (rec) {
            lv_obj_set_style_bg_color(sTalkBtn,
                sBlinkOn ? lv_color_hex(0x1A1814) : lv_color_hex(0x2A2218), LV_PART_MAIN);
            lv_obj_set_style_text_color(sTalkLab, sBlinkOn ? C_TALK : C_WHITE, 0);
            if (sTalkHalo) lv_obj_set_style_bg_opa(sTalkHalo, sBlinkOn ? LV_OPA_50 : LV_OPA_20, 0);
        } else {
            lv_obj_set_style_bg_color(sTalkBtn, C_ORANGE, LV_PART_MAIN);
            lv_obj_set_style_text_color(sTalkLab, C_WHITE, 0);
        }
        lv_obj_center(sTalkLab);
    }

    if (sStopBtn && sStopLab) {
        lv_label_set_text(sStopLab, ICON_BAN);
        lv_obj_set_style_text_font(sStopLab, &font_icons, 0);
        if (rec || running) {
            lv_obj_set_style_bg_color(sStopBtn, C_HOT, LV_PART_MAIN);
            lv_obj_set_style_text_color(sStopLab, C_WHITE, 0);
        } else {
            lv_obj_set_style_bg_color(sStopBtn, C_WELL, LV_PART_MAIN);
            lv_obj_set_style_text_color(sStopLab, C_MUTE, 0);
        }
        lv_obj_center(sStopLab);
    }

    if (sDeskBar) {
        if (rec) lv_obj_clear_flag(sDeskBar, LV_OBJ_FLAG_HIDDEN);
        else lv_obj_add_flag(sDeskBar, LV_OBJ_FLAG_HIDDEN);
    }

    paint_lamp();
    if (sPage == PAGE_USAGE) usage_paint();
    if (sPage == PAGE_IDLE) idle_paint();
    if (sPage == PAGE_PLAN) plan_paint();
    quota_chime();
}

void ui_next_page() {
    if (ui_nav_blocked()) return;
    if (sPage == PAGE_IDLE) {
        wake_idle();
        return;
    }
    ui_note_activity();
    if (sPage == PAGE_PLAN) {
        sPage = PAGE_USAGE;
        show_current();
        return;
    }
    if (sPage == PAGE_DESK) {
        sPage = PAGE_USAGE;
        sUsagePage = 0;
        show_current();
        return;
    }
    if (sPage == PAGE_PACK) return;
    if (sPage == PAGE_USAGE) {
        if (sUsagePage < usage_pages() - 1) {
            sUsagePage++;
            usage_paint();
            return;
        }
        sPackFromUsage = true;
        sPage = PAGE_PACK;
        show_current();
        return;
    }
}

void ui_prev_page() {
    if (ui_nav_blocked()) return;
    if (sPage == PAGE_IDLE) {
        wake_idle();
        return;
    }
    ui_note_activity();
    if (sPage == PAGE_PLAN) {
        sPage = PAGE_USAGE;
        show_current();
        return;
    }
    if (sPage == PAGE_DESK) return;
    if (sPage == PAGE_USAGE) {
        if (sUsagePage > 0) {
            sUsagePage--;
            usage_paint();
            return;
        }
        sPage = PAGE_DESK;
        show_current();
        return;
    }
    if (sPage == PAGE_PACK) {
        if (sPackFromUsage) {
            sPage = PAGE_USAGE;
            sUsagePage = usage_pages() - 1;
            if (sUsagePage < 0) sUsagePage = 0;
            show_current();
            return;
        }
        sPage = PAGE_DESK;
        show_current();
    }
}

int ui_page() { return sPage; }
bool ui_is_idle() { return sPage == PAGE_IDLE; }
bool ui_is_pack() { return sPage == PAGE_PACK; }
bool ui_nav_blocked() { return voice_is_recording(); }

void ui_wake_from_idle() { wake_idle(); }

void ui_loop() {
    uint32_t now = millis();
    if (sFlash[0] && now >= sHintUntil) {
        sFlash[0] = 0;
        if (sToast) lv_obj_add_flag(sToast, LV_OBJ_FLAG_HIDDEN);
        ui_refresh_from_status();
    }
    if (sPackSaveAt && now >= sPackSaveAt) {
        sPackSaveAt = 0;
        pack_save();
    }
    if (now - sResetTickAt >= 1000) {
        sResetTickAt = now;
        for (int i = 0; i < LOGO_COUNT; i++) {
            if (sReset[i] > 0) sReset[i]--;
        }
        if (sPage == PAGE_USAGE) usage_paint();
        if (sPage == PAGE_IDLE) idle_paint();
        if (sPage == PAGE_PLAN) plan_paint();
        quota_chime();
        if (!voice_is_recording() && (sPage == PAGE_DESK || sPage == PAGE_USAGE) &&
            now - sActAt > kIdleMs) {
            sPage = PAGE_IDLE;
            show_current();
        }
    }
    if (voice_is_recording()) {
        ui_refresh_from_status();
        if (now - sBlinkAt > 400) {
            sBlinkAt = now;
            sBlinkOn = !sBlinkOn;
            if (sDeskBar) lv_obj_set_style_bg_opa(sDeskBar, sBlinkOn ? LV_OPA_COVER : LV_OPA_30, 0);
            if (sTalkHalo) lv_obj_set_style_bg_opa(sTalkHalo, sBlinkOn ? LV_OPA_50 : LV_OPA_20, 0);
            if (sTalkBtn) {
                lv_obj_set_style_bg_color(sTalkBtn,
                    sBlinkOn ? lv_color_hex(0x1A1814) : lv_color_hex(0x2A2218), LV_PART_MAIN);
            }
            if (sTalkLab) {
                lv_obj_set_style_text_color(sTalkLab, sBlinkOn ? C_TALK : C_WHITE, 0);
            }
            if (sLamp && used_max() >= 90)
                lv_obj_set_style_bg_opa(sLamp, sBlinkOn ? LV_OPA_COVER : LV_OPA_30, 0);
        }
    } else if (!sBlinkOn) {
        sBlinkOn = true;
        if (sDeskBar) lv_obj_set_style_bg_opa(sDeskBar, LV_OPA_COVER, 0);
        if (sTalkHalo) lv_obj_set_style_bg_opa(sTalkHalo, LV_OPA_30, 0);
        if (sLamp) lv_obj_set_style_bg_opa(sLamp, LV_OPA_COVER, 0);
    }
    pack_tick();
    lv_timer_handler();
}
