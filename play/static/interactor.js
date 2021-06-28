import * as C from "./constants.js";

export class Interactor {
    constructor (_interface) {
        this.interface = _interface;
        this.highlightedItem = -1;
        this.actionList = [];
        this.postMoveActionList = [];
        this.actionChoice = 0;
        this.rightClickMode = C.MODE_INVENTORY;
        this.bind();
    };

    bind () {
        this.interface.canvas.bindMapClickHandler(this.processMapClick.bind(this));
        this.interface.canvas.bindInventoryClickHandler(this.processInventoryClick.bind(this));
        this.interface.canvas.bindClickClickHandler(this.processClickClick.bind(this));
    };

    processInventoryClickAny (c, x, y) {
        this.actionList = [];
        this.postMoveActionList = [];
        let item = this.interface.player.inventory[y * 4 + x];

        if (["_", "X"].includes(item)) {
            if (c === C.MOUSE_LEFT) return;
            this.actionList = this.actionList
                .concat({display: "cancel", action: "click_idle", args: []});
            return;
        }
        if (item === "H") {
            for (let option = 0; option < C.CALL_COUNT[this.interface.role]; option++) {
                let display = `inventory_${this.interface.role}_h_${option}`;
                let action = "click_select_call";
                let args = [option];
                this.actionList.push({ display, action, args });
                if (c === C.MOUSE_LEFT) return;
            }
        }

        if (this.interface.role === "a") {
            throw "Attacker equips items, but is not implemented yet. Attacker clicking cape/shrink will emote with it.";
        }

        if (this.interface.role === "s") {
            throw "Attacker equips items, but is not implemented yet.";
        }

        if (this.interface.role === "c") {
            throw "Collector loads eggs, but is not implemented yet.";
        }

        if (this.interface.role === "d") {
            if (["0", "1", "2"].includes(item)) {
                let display = `inventory_${this.interface.role}_${item}`;
                let action = "click_drop_select_food";
                let args = [[y * 4 + x]];
                this.actionList.push({ display, action, args });
            }
        }

        if (this.interface.role === "h") {
            let display = `inventory_${this.interface.role}_${item}`;
            let action = "click_idle";  // Examine.
            let args = [];
            this.actionList.push({ display, action, args });
            // Currently, there's no need whatsoever to highlight items.
            // Clicking on the egg will load it to the nearest hopper.
            // Clicking on the food will do nothing.
            // Clicking on a healer will use a right food (or guess) on it.
            // Clicking on the hopper will load eggs just like the real game functions.

            // if (this.highlightedItem === -1) {
            //     this.highlightedItem = y * 4 + x;
            // } else {
            //     this.highlightedItem = -1;
            // }
        }

        let display = `inventory_${this.interface.role}_${item.toLowerCase()}_b`;
        let action = "click_destroy_items";
        let args = [[y * 4 + x]];
        this.actionList.push({ display, action, args });

        this.actionList = this.actionList
            .concat({display: "cancel", action: "click_idle", args: []});

        return;
    };

    processInventoryClick (event) {
        // Getting c is necessary to call from horn. We might as well add destroy options then.
        // Either way, shift click is more important.
        // TODO: Implement shift-clicking.
        event.stopPropagation();
        event.preventDefault();

        this.actionChoice = 0;

        if (this.interface.canvas.rightClickMenuRectangle) {
            if (this.processRightClickMenuChoice(event))
                return false;
        }

        const { c, x, y } = this.interface.canvas.convertPhysicalClickToLogicalClick(event, C.MODE_INVENTORY);
        this.processInventoryClickAny(c, x, y);

        if (c === C.MOUSE_RIGHT) {
            this.rightClickMode = C.MODE_INVENTORY;
            this.openRightClickMenu(event);
            return false;
        }

        const { action, args } = this.actionList[this.actionChoice];

        if (c === C.MOUSE_LEFT) {
            console.log("LEFT CLICK", this.actionList);
            this.interface.sendAction(action, args);
            return false;
        }

        return false;
    };

    processMapClickMove (c, x, y) {
        let display = "walk";
        let action = "click_move";
        let args = [x, y];
        this.actionList.push({ display, action, args });
    };

    processMapClickNpc (c, x, y) {
        let is_attacker = ["a", "s"].includes(this.interface.role);

        if (this.interface.penancePerGameTile["d"][y][x].length > 0) {
            for (let runner of this.interface.penancePerGameTile["d"][y][x]) {
                let display = "map_d_runner";
                let action = "click_idle";
                let args = [];
                this.postMoveActionList.push({ display, action, args });
            }
        }

        if (this.interface.penancePerGameTile["h"][y][x].length > 0) {
            let is_healer = this.interface.role === "h";
            let correct_call = this.interface.player.correct_call;
            for (let healer of this.interface.penancePerGameTile["h"][y][x]) {
                let display = is_healer ? `map_h_use_${correct_call}` : "map_h_healer";
                let action = is_healer ? "click_use_poison_food" : "click_idle";
                let args = is_healer ? [correct_call, healer.uuid] : [];
                this.postMoveActionList.push({ display, action, args });
            }
        }

        if (this.interface.penancePerGameTile["a"][y][x].length > 0) {
            for (let fighter of this.interface.penancePerGameTile["a"][y][x]) {
                let display = is_attacker ? "map_a_fighter" : "map_a_fighter_x";
                let action = is_attacker ? "click_attack" : "click_idle";
                let args = is_attacker ? [fighter.uuid] : [];
                this.postMoveActionList.push({display, action, args});
            }
        }

        if (this.interface.penancePerGameTile["s"][y][x].length > 0) {
            for (let ranger of this.interface.penancePerGameTile["s"][y][x]) {
                let display = is_attacker ? "map_a_ranger" : "map_a_ranger_x";
                let action = is_attacker ? "click_attack" : "click_idle";
                let args = is_attacker ? [ranger.uuid] : [];
                this.postMoveActionList.push({ display, action, args });
            }
        }
    };

    processMapClickItem (c, x, y) {
        for (let key in this.interface.droppedItemsPerGameTile) {
            if (!this.interface.droppedItemsPerGameTile.hasOwnProperty(key)) continue;
            if (key === "food" && (this.interface.role !== "d" || c === C.MOUSE_LEFT)) continue;
            if (key === "hnls" && this.interface.role !== "d") continue;
            if (key === "eggs" && this.interface.role !== "c") continue;
            for (let item of this.interface.droppedItemsPerGameTile[key][y][x]) {
                let number;

                if (key === "food" || key === "eggs") {
                    number = item.which;
                }

                if (key === "hnls") {
                    number = item._ === "Hammer" ? 3 : 4;
                }

                let display = `map_d_item_${number}`;
                let action = "click_pick_item";
                let args = [item.uuid];
                this.actionList.push({ display, action, args });
                if (c === C.MOUSE_LEFT) return;
            }
        }
    };

    processMapClickGameObject (c, x, y) {
        let post_i = 0;
        if (C.ROLE_TO_DISPENSER[this.interface.role] === this.interface.game.original_map[y][x]) {
            if (this.interface.role === "h") {
                // Healer logic, since healer has multiple options.
                for (let option of C.HEALER_DISPENSER_OPTIONS) {
                    let display = `map_h_disp_${option}`;
                    let action = Number.isNaN(+option) ? "click_idle" : "click_use_dispenser";
                    let args = Number.isNaN(+option) ? [] : [+option];
                    post_i++;
                    if (post_i > 4) {
                        this.postMoveActionList.push({ display, action, args });
                    } else {
                        this.actionList.push({ display, action, args });
                    }
                    if (c === C.MOUSE_LEFT) return;
                }
            } else {
                let display = `map_${this.interface.role}_disp_5`;
                let action = "click_use_dispenser";
                let args = [];
                this.actionList.push({ display, action, args });
                if (c === C.MOUSE_LEFT) return;
            }
        }

        if (C.TRAPS.includes(this.interface.game.original_map[y][x]) && this.interface.role === "d") {
            let which = this.interface.game.original_map[y][x] < "a" ?
                this.interface.game.wave.game_objects.trap :
                this.interface.game.wave.game_objects.west_trap;
            if (which.charges !== 2) {
                let display = `map_d_trap_${which.charges}`;
                let action = "click_repair_trap";
                let args = [which.which];
                this.actionList.push({ display, action, args });
                if (c === C.MOUSE_LEFT) return;
            }
        }

        // TODO: Hopper (coll only), cannon (any).
        // TODO: We'll implement pool and ladder later.

    };

    processMapClickAny (c, x, y) {
        // For left click, order is: Npc -> GameObject -> Item -> Move.
        // The real order in the game is different, but it would make repairing trap hell.
        // For right click, the order is the same, but only the 4 top-most GameObject options are displayed
        // in their proper position. The rest are post-appended through postMoveActionList.
        this.actionList = [];
        this.postMoveActionList = [];

        let fns = [
            this.processMapClickNpc,
            this.processMapClickGameObject,
            this.processMapClickItem,
            this.processMapClickMove,
        ];

        for (let fn of fns) {
            fn.bind(this)(c, x, y);
            if (c === C.MOUSE_LEFT && this.actionList.length > 0) return;
        }

        this.actionList = this.actionList
            .concat(this.postMoveActionList)
            .concat({display: "cancel", action: "click_idle", args: []});
    };

    openRightClickMenu (event) {
        this.interface.canvas.drawRightClickMenu(
            event,
            this.actionList
        );
    };

    processRightClickMenuChoice (event) {
        // Makes use of this.canvas.rightClickMenuRectangle to process an event.
        // Returns true if the click was within the right click menu, so that the click doesn't
        // fall through.
        if (event.button !== C.MOUSE_LEFT) return false;


        if (!this.interface.canvas.rightClickMenuRectangle) return false;
        if (
            this.interface.canvas.rightClickMenuRectangle.x_min - event.clientX > 0 ||
            this.interface.canvas.rightClickMenuRectangle.y_min - event.clientY > 0 ||
            event.clientX - this.interface.canvas.rightClickMenuRectangle.x_max > 0 ||
            event.clientY - this.interface.canvas.rightClickMenuRectangle.y_max > 0
        ) {
            return false;
        }

        let y = event.clientY - this.interface.canvas.rightClickMenuRectangle.y_min;
        y -= C.RC['top_front'].naturalHeight;
        y = Math.floor(y / C.MENU_ITEM_HEIGHT);
        if (y < 0) return false;
        this.actionChoice = y;
        const { action, args } = this.actionList[this.actionChoice];
        this.interface.sendAction(action, args);
        if (this.rightClickMode === C.MODE_MAP)
            this.interface.canvas.startClickAnimation(event, action === "click_move" ? C.CLICK_YELLOW : C.CLICK_RED);

        return true;
    }

    processMapClick (event) {
        event.stopPropagation();
        event.preventDefault();

        this.actionChoice = 0;

        if (this.interface.canvas.rightClickMenuRectangle) {
            if (this.processRightClickMenuChoice(event))
                return false;
        }

        const { c, x, y } = this.interface.canvas.convertPhysicalClickToLogicalClick(event, C.MODE_MAP);
        this.processMapClickAny(c, x, y);

        if (c === C.MOUSE_RIGHT) {
            this.rightClickMode = C.MODE_MAP;
            this.openRightClickMenu(event);
            return false;
        }

        const { action, args } = this.actionList[this.actionChoice];

        if (c === C.MOUSE_LEFT) {
            console.log("LEFT CLICK", this.actionList);
            this.interface.sendAction(action, args);
            this.interface.canvas.startClickAnimation(event, action === "click_move" ? C.CLICK_YELLOW : C.CLICK_RED);
            return false;
        }

        return false;
    };

    processClickClick (event) {
        if (this.interface.canvas.rightClickMenuRectangle) {
            if (this.processRightClickMenuChoice(event))
                return false;
        }
    }
}

/*

let itemFn = function (event) {
    if (this.classList.contains("dpickable") && player.access_letter === "d") {
        console.log(this, this.uuids)
        transmit("click_pick_item", [this.uuids[this.uuids.length - 1]]);
        // TODO: BUILD right clicking to pick items under items.
        click(RED, event);
    }
}


let dispenserFn = function (event) {
    // Clicking any dispenser in the dispenser area will make you use your right dispenser.
    transmit("click_use_dispenser", []);  // With a None for argument (default stock for heal).
    // To stock something different, please right click the dispenser area.
    // TODO: BUILD right clicking the dispenser area.
    click(RED, event);
}

*/
