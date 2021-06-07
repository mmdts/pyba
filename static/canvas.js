import $ from "./jquery.js";
import * as C from "./constants.js";

const $mapCanvas = $("#map");
const $mapElementsCanvas = $("#map_elements");
const $inventoryCanvas = $("#inventory");
const $clickCanvas = $("#right_click");
const $infoDiv = $("#info");

let $game = $(".game");
$mapCanvas[0].width = $mapElementsCanvas[0].width = C.TILE_SIZE * C.MAP_WIDTH;
$mapCanvas[0].height = $mapElementsCanvas[0].height = C.TILE_SIZE * C.MAP_HEIGHT;
$clickCanvas[0].width = $game.width() + 2 * C.MAX_RIGHT_CLICK_OVERFLOW;
$clickCanvas[0].height = $game.height() + C.MAX_RIGHT_CLICK_OVERFLOW;
$inventoryCanvas[0].width = C.INVENTORY_COLS * C.INVENTORY_ITEM_WIDTH;
$inventoryCanvas[0].height = C.INVENTORY_ROWS * C.INVENTORY_ITEM_HEIGHT;


let mapCtx = $mapCanvas[0].getContext("2d");
let mapElementsCtx = $mapElementsCanvas[0].getContext("2d");
let inventoryCtx = $inventoryCanvas[0].getContext("2d");
let clickCtx = $clickCanvas[0].getContext("2d");


export class Canvas {
    constructor () {
        this.drawn = false;
        this.clickFrame = -2;
        this.clickColor = C.CLICK_YELLOW;
        this.clickLocation = {x: 0, y: 0};
        this.rightClickMenuRectangle = false;

        clickCtx.imageSmoothingEnabled = false;
    };

    drawMap (mapArray) {
        for (let i = 0; i < C.MAP_HEIGHT; i++) { // i is y, j is x.
            for (let j = 0; j < C.MAP_WIDTH; j++) {
                mapCtx.beginPath();
                mapCtx.rect(j * C.TILE_SIZE, i * C.TILE_SIZE, C.TILE_SIZE, C.TILE_SIZE);
                mapCtx.linewidth = 1;
                mapCtx.strokeStyle = "#faebd706";
                mapCtx.fillStyle = C.COLORS["_"];
                if (C.HIGH.includes(mapArray[i][j])) {
                    mapCtx.fillStyle = C.COLORS["^"];
                }
                if (C.COLORS[mapArray[i][j]] !== undefined) {
                    mapCtx.fillStyle = C.COLORS[mapArray[i][j]];
                }
                mapCtx.fill();
                mapCtx.stroke();
                mapCtx.closePath();
                if (C.GAME_OBJECTS[mapArray[i][j].toLowerCase()] !== undefined) {
                    mapCtx.drawImage(C.GAME_OBJECTS[mapArray[i][j].toLowerCase()],
                        j * C.TILE_SIZE, i * C.TILE_SIZE, C.TILE_SIZE, C.TILE_SIZE);
                }
            }
        }
        this.drawn = true;
    };

    drawTileObject (image, x, y) {
        mapElementsCtx.drawImage(image, x * C.TILE_SIZE, y * C.TILE_SIZE, C.TILE_SIZE, C.TILE_SIZE);
    }

    drawMapElements (mapArray, droppedItems, role) {
        mapElementsCtx.clearRect(0, 0, $mapElementsCanvas[0].width, $mapElementsCanvas[0].height);
        for (let i = 0; i < C.MAP_HEIGHT; i++) { // i is y, j is x.
            for (let j = 0; j < C.MAP_WIDTH; j++) {
                if (role === "d" || role === "_") {
                    for (const item of droppedItems["food"][i][j]) {
                        this.drawTileObject(C.ITEMS["d" + item.which.toString()], j, i);
                    }
                    for (const item of droppedItems["hnls"][i][j]) {
                        let type = item["_"].toLowerCase();
                        if (type === "hammer") {
                            this.drawTileObject(C.ITEMS["d3"], j, i);
                            continue;
                        }
                        if (type === "logs") {
                            this.drawTileObject(C.ITEMS["d4"], j, i);
                            continue;
                        }
                        throw "Something that is neither hammer nor logs was in hnl array."
                    }
                }

                for (const item of droppedItems["eggs"][i][j]) {
                    this.drawTileObject(C.ITEMS["c" + item.which.toString()], j, i);
                }

                if (C.PLAYERS[mapArray[i][j]]?.naturalHeight > 0) {
                    this.drawTileObject(C.PLAYERS[mapArray[i][j]], j, i);
                }

                if (C.PENANCE[mapArray[i][j]]?.naturalHeight > 0) {
                    this.drawTileObject(C.PENANCE[mapArray[i][j]], j, i);
                }
            }
        }
    };

    drawInventoryObject (image, x, y) {
        inventoryCtx.drawImage(
            image,
            x * C.INVENTORY_ITEM_WIDTH, y * C.INVENTORY_ITEM_HEIGHT,
            C.INVENTORY_ITEM_WIDTH, C.INVENTORY_ITEM_HEIGHT
        );
    }

    drawInventory (role, inventoryArray, highlightedItem = -1) {
        inventoryCtx.clearRect(0, 0, $mapElementsCanvas[0].width, $mapElementsCanvas[0].height);
        for (let k = 0; k < inventoryArray.length; k++) {
            let i = Math.floor(k / 4);  // Which row
            let j = k % 4;  // Which column.

            if (["_", "X"].includes(inventoryArray[k])) {
                continue;
            }
            if (inventoryArray[k] === "H") {
            this.drawInventoryObject(C.ITEMS["H"], j, i);
            }
            if (C.ITEMS[role + inventoryArray[k]] === undefined) {
                continue;
            }
            if (highlightedItem === k) {
                inventoryCtx.beginPath();
                inventoryCtx.rect(
                    j * C.INVENTORY_ITEM_WIDTH, i * C.INVENTORY_ITEM_HEIGHT,
                    C.INVENTORY_ITEM_WIDTH, C.INVENTORY_ITEM_HEIGHT
                );
                inventoryCtx.fillStyle = "#faebd706";
                inventoryCtx.fill();
                inventoryCtx.closePath();
            }

            this.drawInventoryObject(C.ITEMS[role + inventoryArray[k]], j, i);
        }
    }

    startClickAnimation (event, color = C.CLICK_YELLOW) {
        this.clickFrame = 0;
        this.clickColor = color;
        let rect = $clickCanvas[0].getBoundingClientRect();
        this.clickLocation = {
            x: event.clientX - rect.left,
            y: event.clientY - rect.top,
        }
    };

    drawClick () {
        if (this.clickFrame === -2) {
            return
        }

        if (this.clickFrame === -1) {
            clickCtx.clearRect(0, 0, $clickCanvas[0].width, $clickCanvas[0].height);
            this.clickFrame = -2;
            return
        }

        clickCtx.clearRect(0, 0, $clickCanvas[0].width, $clickCanvas[0].height);
        clickCtx.drawImage(
            C.CLICK_FRAMES[this.clickColor][this.clickFrame],
            this.clickLocation.x - C.CLICK_SIZE / 2,
            this.clickLocation.y - C.CLICK_SIZE / 2,
            C.CLICK_SIZE,
            C.CLICK_SIZE
        );
        this.clickFrame++;

        if (this.clickFrame === C.CLICK_FRAMES[this.clickColor].length) {
            this.clickFrame = -1;
        }
    }

    clearRightClickMenu (event) {
        if (!this.rightClickMenuRectangle) return;
        if (
            this.rightClickMenuRectangle.x_min - event.clientX > C.RIGHT_CLICK_CLOSE_THRESHOLD ||
            this.rightClickMenuRectangle.y_min - event.clientY > C.RIGHT_CLICK_CLOSE_THRESHOLD ||
            event.clientX - this.rightClickMenuRectangle.x_max > C.RIGHT_CLICK_CLOSE_THRESHOLD ||
            event.clientY - this.rightClickMenuRectangle.y_max > C.RIGHT_CLICK_CLOSE_THRESHOLD
        ) {
            clickCtx.clearRect(0, 0, $clickCanvas[0].width, $clickCanvas[0].height);
            this.rightClickMenuRectangle = false;
        }
    };

    writeInfo (infoArray) {
        $infoDiv.text(infoArray.join("\n"));
    };

    drawRightClickMenu (event, actionList) {
        clickCtx.clearRect(0, 0, $clickCanvas[0].width, $clickCanvas[0].height);
        this.clickFrame = -2;  // Reset any click animation.
        let rect = $clickCanvas[0].getBoundingClientRect();
        let x = event.clientX - rect.left;
        let y = event.clientY - rect.top;

        // Draw: back -> top_back -> top_front -> options -> cancel -> bottom -> right
        let width = C.RC['top_front'].naturalWidth + C.MENU_PADDING;
        let height = C.RC['top_front'].naturalHeight;

        for (let item of actionList) {
            if (!C.RC[item.display]) {
                console.log("UNDEFINED ITEM", item.display);
                continue;
            }
            let itemWidth = C.RC[item.display].naturalWidth + C.MENU_PADDING;
            width = width < itemWidth ? itemWidth : width;
            height += C.RC[item.display].naturalHeight;
        }
        height += C.RC['bottom'].naturalHeight;  // Choose option text
        width += C.RC['right'].naturalWidth;

        this.rightClickMenuRectangle = {  // This is for closing through mouse move.
            x_min: event.clientX - width / 2,
            y_min: event.clientY,
            x_max: event.clientX + width / 2,
            y_max: event.clientY + height,
        };

        let y_stepper = y;
        let x_start = x - width / 2;

        // Brown background
        clickCtx.drawImage(C.RC['back'], x - width / 2, y, width, height);

        // Choose zone
        clickCtx.drawImage(C.RC['top_back'],
            x_start, y,
            width - 1, C.RC['top_back'].naturalHeight
        );
        clickCtx.drawImage(
            C.RC['top_front'],
            x_start, y,
            C.RC['top_front'].naturalWidth, C.RC['top_front'].naturalHeight
        );
        y_stepper += C.RC['top_front'].naturalHeight;

        // The options
        for (let item of actionList) {
            if (!C.RC[item.display]) {
                continue;
            }
            clickCtx.drawImage(
                 C.RC[item.display],
                x_start, y_stepper,
                 C.RC[item.display].naturalWidth, C.RC[item.display].naturalHeight
            );
            y_stepper += C.RC[item.display].naturalHeight;
        }

        // Bottom black border
        clickCtx.drawImage(
            C.RC['bottom'],
            x_start + 1, y + height - 2,
            width - 2, C.RC['bottom'].naturalHeight
        );
        // Right black border
        clickCtx.drawImage(
            C.RC['right'],
            x_start + width - 2, y + C.RC['top_front'].naturalHeight - 1,
            C.RC['right'].naturalWidth, height - C.RC['top_front'].naturalHeight
        );
    };

    bindMapClickHandler (handler) {
        $mapElementsCanvas.on('click', handler);
        $mapElementsCanvas.on('contextmenu', handler);
    };

    bindInventoryClickHandler (handler) {
        $inventoryCanvas.on('click', handler);
        $inventoryCanvas.on('contextmenu', handler);
        $inventoryCanvas.on('click', (function (event) {
            if (event.button === C.MOUSE_LEFT) {
                this.rightClickMenuRectangle = false;
                clickCtx.clearRect(0, 0, $clickCanvas[0].width, $clickCanvas[0].height);
            }
        }).bind(this));
    };

    bindClickClickHandler (handler) {
        $(document).on('mousemove', this.clearRightClickMenu.bind(this));
        $game.on('click', handler);
        $game.on('contextmenu', function (event) {
            event.stopPropagation();
            event.preventDefault();
            return false;
        });
    };

    convertPhysicalClickToLogicalClick (event, mode = C.MODE_MAP) {
        // Returns the coordinates of the tile clicked, and the click type (right / left).
        if (mode === C.MODE_MAP) {
            let rect = $mapElementsCanvas[0].getBoundingClientRect();
            return {
                x: Math.floor((event.clientX - rect.left) / C.TILE_SIZE),
                y: Math.floor((event.clientY - rect.top) / C.TILE_SIZE),
                c: event.button,
            }
        }
        if (mode === C.MODE_INVENTORY) {
            let rect = $inventoryCanvas[0].getBoundingClientRect();
            return {
                x: Math.floor((event.clientX - rect.left) / C.INVENTORY_ITEM_WIDTH),
                y: Math.floor((event.clientY - rect.top) / C.INVENTORY_ITEM_HEIGHT),
                c: event.button,
            }
        }
        throw "Invalid mode provided to convertPhysicalClickToLogicalClick. " +
              "Please use one of the valid mode constants.";
    };
}
