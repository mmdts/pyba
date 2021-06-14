// Keep in mind that this changes if the respective constants in the server change.
/**
 * @typedef {number} enum
 */


// Inventory pixel values
/** @type {number} */
export const INVENTORY_COLS = 4;
/** @type {number} */
export const INVENTORY_ROWS = 7;
/** @type {number} */
export const INVENTORY_SIZE = INVENTORY_COLS * INVENTORY_ROWS;
/** @type {number} */
export const INVENTORY_ITEM_WIDTH = 42;
/** @type {number} */
export const INVENTORY_ITEM_HEIGHT = 36;


// Map pixel values
/** @type {number} */
export const MAP_WIDTH = 39;
/** @type {number} */
export const MAP_HEIGHT = 37;
/** @type {number} */
export const TILE_SIZE = 20;
/** @type {number} */
export const MAX_RIGHT_CLICK_OVERFLOW = 70;


// Map letters
/** @type {string} */
export const ROLES = "dhacs";
/** @type {string} */
export const HIGH = "^krKR";
/** @type {string} */
export const TRAPS = "Tt";
/** @type {string} */
export const CANNONS = "Kk";
/** @type {string} */
export const HOPPERS = "Rr";
/** @type {string} */
export const POOL = "P";


// Role based map letters
/** @type {{a: string, c: string, d: string, h: string}} */
export const ROLE_TO_DISPENSER = { "a": "q", "c": "y", "d": "w", "h": "e", };


// Calls
/** @type {{a: number, c: number, d: number, h: number}} */
export const CALL_COUNT = { "a": 3, "c": 4, "d": 3, "h": 3, }
/** @type {{a: string[], c: string[], d: string[], h: string[]}} */
export const NAMES = {
    "a": ["", "", "", ""],
    "c": ["Red", "Green", "Blue"],
    "d": ["Tofu", "Crackers", "Worms"],
    "h": ["P Tofu", "P Worms", "P Meat"],
};
/** @type {{a: string, c: string, d: string, h: string}} */
export const CALL_PAIR = { "a": "c", "c": "a", "d": "h", "h": "d"};


// Right click pixel values
/** @type {number} */
export const RIGHT_CLICK_CLOSE_THRESHOLD = 30;
/** @type {number} */
export const MENU_PADDING = 4;
/** @type {number} */
export const MENU_ITEM_HEIGHT = 15;
/** @type {string[]} */


// Right click options
export const RIGHT_CLICK_OPTIONS_ARRAY = [
    "cancel", "back", "bottom", "right", "top_back", "top_front", "walk",
    "map_d_disp_5", "map_a_disp_5", "map_c_disp_5", "map_h_disp_5", "map_h_disp_6",
    "map_h_disp_0", "map_h_disp_1", "map_h_disp_x", "map_h_disp_2",
    "map_d_item_0", "map_d_item_1", "map_d_item_2", "map_d_item_3", "map_d_item_4",
    "map_c_item_0", "map_c_item_1", "map_c_item_2", "map_c_load", "map_cannon",
    "map_a_fighter", "map_a_ranger", "inventory_d_h_2", "map_h_healer",
    "map_d_trap_0", "map_d_trap_1", "inventory_d_h_b", "map_d_runner",
    "inventory_d_0", "inventory_d_1", "inventory_d_2", "inventory_d_h_0",
    "inventory_d_0_b", "inventory_d_1_b", "inventory_d_2_b", "inventory_d_h_1",
];
/** @type {string[]} */
export const HEALER_DISPENSER_OPTIONS = ["5", "6", "0", "1", "x", "2"];  // In order!
/** @type {object} */
export const RC = {};
for (const item of RIGHT_CLICK_OPTIONS_ARRAY) {
    const image = new Image();
    image.src = `rightclick/${item}.png`;
    RC[item] = image;
}


// Room time modes
/** @type {enum} */
export const ROOM_DELAY = 0;
/** @type {enum} */
export const ROOM_PAUSE = 1;
/** @type {enum} */
export const ROOM_F_FWD = 2;


// Mouse buttons
/** @type {enum} */
export const MOUSE_LEFT = 0;
/** @type {enum} */
export const MOUSE_RIGHT = 2;


// Right click zones
/** @type {enum} */
export const MODE_MAP = 0;
/** @type {enum} */
export const MODE_INVENTORY = 1;

// Click types
/** @type {enum} */
export const CLICK_YELLOW = 0;
/** @type {enum} */
export const CLICK_RED = 1;


// Click animation constants
export const CLICK_SIZE = 14;
export const CLICK_FRAMES = {
    0: ["clicks/y0.png", "clicks/y1.png", "clicks/y2.png", "clicks/y3.png"],
    1: ["clicks/r0.png", "clicks/r1.png", "clicks/r2.png", "clicks/r3.png"],
};
for (let i = 0; i < 2; i++) {
    for (let j = 0; j < CLICK_FRAMES[i].length; j++) {
        const image = new Image();
        image.src = CLICK_FRAMES[i][j];
        CLICK_FRAMES[i][j] = image;
    }
}


// Game images
/** @type {object} */
export const GAME_OBJECTS = {
    "t": "gameobjects/trap.png",
    "k": "gameobjects/cannon.png",
    "r": "gameobjects/hopper.png",
};
/** @type {object} */
export const PLAYERS = {
    "E": "roles/h.png",
    "Q": "roles/a.png",
    "Z": "roles/s.png",
    "W": "roles/d.png",
    "Y": "roles/c.png",
};
/** @type {object} */
export const PENANCE = {
    "@": "penance/h.png",
    "%": "penance/d.png",
    "&": "penance/s.png",
    "?": "penance/a.png",
};
/** @type {object} */
export const ITEMS = {
    "h0": "items/h0.png",
    "h1": "items/h1.png",
    "h2": "items/h2.png",
    "d0": "items/d0.png",
    "d1": "items/d1.png",
    "d2": "items/d2.png",
    "d3": "items/d3.png",
    "d4": "items/d4.png",
    "c0": "items/c0.png",
    "c1": "items/c1.png",
    "c2": "items/c2.png",
    "H": "items/horn.png",
};
for (let object of [GAME_OBJECTS, PLAYERS, PENANCE, ITEMS]) {
    for (const key in object) {
        if (object.hasOwnProperty(key)) {
            const image = new Image();
            image.src = object[key];
            object[key] = image;
        }
    }
}


// Map colors
/** @type {object} */
export const COLORS = {
    "_": "#55430e",  //The default. Used for · . a s h c d 1 2 3 4 5 6 7 B S A D H L l m M z O o t T
    "^": "#c6b46f",  // High ground. Used for ^ k r K R
    "#": "#938258",
    "$": "#bda977",
    "P": "#42660c",
    "X": "#00000066",
    "q": "#ff0000",
    "w": "#0000ff",
    "e": "#00ff00",
    "y": "#ffff00",
};
