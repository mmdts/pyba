export class Game {
    /**
     * A Game is simply an object with the following properties that got classified.
     *
     * @typedef {object} Game
     *
     * @param {Game?} gameObject
     * @returns {Game}
     */
    constructor (gameObject) {
        return gameObject ?? {
            "tick": null,  // Check for tick when deciding whether the game exists.
            "text": [],
            "players": {},
            "print_map": [],
            "original_map": [],
            "wave": {
                "correct_calls": [],
                "start_tick": null,
                "relative_tick": null,
                "calls": [],
                "number": null,
                "end_flag": null,
                "game_objects": {
                    "west_cannon": null,
                    "cannon": null,
                    "west_hopper": null,
                    "hopper": null,
                    "west_trap": null,
                    "trap": null,
                },
                "dropped_food": [],
                "dispensers": {},
                "dropped_eggs": [],
                "dropped_hnls": [],
                "penance": {},
            },
        };
    };
}

export class Locatable {
    /**
     * A Locatable is simply an object with the following properties that got classified.
     * Note that these are all the properties of a Locatable, regardless of its type.
     *
     * @typedef {object} Locatable
     *
     * @param {Locatable?} locatableObject
     * @returns {Locatable}
     */
    constructor (locatableObject) {
        return locatableObject ?? {
            "uuid": null,
            "location": [],
            "_": null,
            "inventory": [],
            "post_move_action_queue": null,  // Length of the PMAC.
            'busy_i': null,
            "calls_with": null,
            "destination": null,
            "pathing_queue": [],
            "followee": null,
            "follow_type": null,
            "follow_allow_under": null,
            "is_running": null,
            "followee_last_found": [],
            "CALL_COUNT": null,
            "INVENTORY_SPACE": null,
            "correct_call": null,
            "required_call": null,
            "received_call": null,
            "sent_call": null,
            "name": null,
            "spec_restore_i": null,
            "spec": null,
            "gear_bonus": null,
            "is_stalling": null,
            "stall_queue": null,
            "access_letter": null,
            "which": null,
            "is_correct": null,
            "charges": null,
        };
    }
}
