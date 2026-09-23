// Rooftop level. Tiles: one char per 16px cell, see LEGEND. Props: [name, x, y] with
// (x, y) = bottom-center of the sprite in world pixels (its "feet").

export const TILE = 16;

// '.' floor (random concrete variant, sometimes part of a big slab), ',' dark floor, 'r' rust, 'g' grate, 'm' membrane,
// 'v' gravel, 'a' arrow, '<' '-' '=' '>' neon strip, 'C' wall cap (solid), 'W' wall face,
// 'G' wall graffiti, 'N' wall neon, 'P' wall pipes, 'R' wall with rail (solid).
// A tile name repeated in a list is picked more often: plain slabs are common, marked ones rare.
export const LEGEND = {
  ".": [...Array(12).fill("floor_a"), ...Array(6).fill("floor_g"), ...Array(6).fill("floor_h"),
        ...Array(3).fill("floor_i"), "floor_c", "floor_c", "floor_f", "floor_f", "floor_d",
        "floor_j", "floor_k", "floor_l", "floor_m", "floor_n"],
  ",": ["floor_dark1", "floor_dark2", "floor_dark3", "floor_dark4"], "b": ["floor_b", "floor_e"],
  "r": ["floor_rust"], "g": ["grate"], "m": ["membrane", "membrane_b"], "v": ["gravel", "gravel_b"],
  "a": ["floor_arrow"],
  "<": ["neon_l"], "-": ["neon_m1"], "=": ["neon_m2"], ">": ["neon_r"],
  "C": ["wall_cap"], "W": ["wall_face"], "G": ["wall_graffiti"], "N": ["wall_neon"],
  "P": ["wall_pipes"], "R": ["wall_rail"],
};
// Big 32x32 slabs: this share of the aligned 2x2 blocks of plain floor ('.') become one slab.
// Each set is four tiles NAME_tl NAME_tr NAME_bl NAME_br with joints only on the outer edge.
export const SLABS = { chance: 0.15, sets: ["slab_a", "slab_b", "slab_c"] };
export const SOLID_TILES = new Set(["C", "W", "G", "N", "P", "R"]);

export const MAP = [
  "CCCCCCCCCCCCCCCCCCCCCCCCCCCC",
  "CWWGWWNWWWPWWWWWWNWWGWWWPWWC",
  "C..,....b....mmm......,...vC",
  "C.......,....mmm..........vC",
  "C.b.......r.........b......C",
  "C...,..........,...........C",
  "C.....<--=-=>..............C",
  "C..........b.......,.......C",
  "C.,..........r.........b...C",
  "C........a..........<-=-=>.C",
  "C...b..........,...........C",
  "C.......mm...........,.....C",
  "C.......mm....b.......r....C",
  "C..,.............,.........C",
  "C.....................b....C",
  "RRRRRRRRRRRRRRRRRRRRRRRRRRRR",
];

export const PROPS = [
  // back wall row
  ["vending_machine", 34, 62], ["dumpster", 62, 60], ["ac_unit", 104, 46], ["ac_unit", 126, 46],
  ["potted_plant", 150, 44], ["water_tank", 244, 60], ["fire_barrel", 276, 64],
  ["mushroom_planter", 312, 60], ["satellite_dish", 352, 52], ["antenna_mast", 378, 50],
  ["crates", 422, 62],
  // hangout corner
  ["table", 86, 124], ["chair", 64, 120], ["chair", 110, 118], ["stool", 88, 138],
  ["bench", 150, 102], ["trash_bag", 30, 96], ["trash_bag", 42, 104], ["cardboard_box", 26, 124],
  // right side
  ["neon_sign", 340, 138], ["cardboard_box", 424, 104], ["crates", 424, 126],
  ["holo_projector", 400, 150],
  // lower area
  ["cable_spool", 206, 206], ["potted_plant", 30, 228], ["trash_bag", 424, 226],
  // parked hover cars (palette variants of flycar_parked)
  ["flycar_parked_red", 104, 214], ["flycar_parked_taxi", 296, 238],
];

export const DECALS = [
  ["roof_hatch", 196, 64], ["warning_stripe", 196, 80], ["drain_grate", 232, 186],
  ["neon_puddle", 250, 150], ["neon_puddle", 300, 196], ["neon_puddle", 120, 176],
  ["oil_stain", 280, 110], ["oil_stain", 60, 190], ["cables", 176, 188], ["cables", 360, 70],
  ["drone_pad", 384, 222], ["pizza_box", 116, 138], ["noodle_cup", 70, 132],
  ["noodle_cup", 100, 146], ["can_red", 132, 132], ["can_blue", 48, 78], ["can_red", 290, 160],
  ["paper", 160, 150], ["paper", 330, 100], ["paper", 220, 230], ["butts", 180, 118],
  ["butts", 268, 84], ["can_blue", 372, 182], ["paper", 60, 214],
];

// Lighting: night ambient, cool moon from the top-left, and shared shadow settings.
// Glowing props become point lights automatically; neon tiles add their own (see engine).
export const LIGHTING = {
  ambient: "#2a2b48",
  moon: { color: "#4c5884", dir: [0.62, 0.42], length: 0.75, shadow: 0.8 },
  shadow: 0.88,     // fraction of a light removed inside its shadow
  levels: 12,       // flat-shaded bands for light falloff and shadow edges
  maxShadow: 60,    // px, caps shadows from low lights
  carLight: "#8a92b8",  // light on things above the roof (the flying car): moon + ambient
  fadeTo: 0.15,     // shadow strength left at the far tip (1 = no fade)
  blur: 2,          // penumbra: box-blur radius (2 passes) applied to shadow masks
  contact: 0.72,    // contact shadow darkness at the center of a footprint
  contactSpread: 3, // px the contact shadow reaches beyond the footprint
  contactBlur: 2,   // box-blur radius (2 passes) softening the contact shadow's edge
};

// Flyover: an unseen vehicle crossing above the roof; only its lights are visible.
export const FLYOVER = {
  every: [2500, 8000],   // ms between spawns (random); cars overlap, each finishes its pass
  speed: 260,            // px/s
  height: 44,            // px above the roof (sprite drawn this much higher on screen)
  ahead: 70,             // headlight aim point, px ahead of the craft (on the ground)
  margin: 360,
  bloom: 0.22,           // share of the flyover light added on top (overexposure)
  cars: ["flycar", "flycar_red", "flycar_taxi", "flycar_police", "flycar_black"],
  bob: 2,                // hover bob amplitude, px           // start/end this far outside the view so the light glides in/out
  headlight: { color: "#e8f4ff", intensity: 1.8, range: 80, inner: 0.2, outer: 0.48 },
  tail: { color: "#ff2a2a", intensity: 0.9, radius: 34, spread: 6, back: 18 },
  under: { color: "#5a7cff", intensity: 0.18, radius: 70 },
};
