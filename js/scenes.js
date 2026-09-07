/* DOR-LIO project page — scene registry.
 *
 * To add a new interactive scene, export your map with
 *   tools/pcd_to_ply.py -i your_map.pcd -o data/your_scene.ply ...
 * then register it below. Restart-free: it is plain JS. */
(function (global) {
  'use strict';

  const SCENES = {
    // Scenes shown in the single-map "Point Cloud Explorer".
    explorer: [
      {
        id: 'campus',
        title: 'Campus (handheld MID360)',
        file: 'data/campus_clean.ply',
        badges: ['real data', 'DOR-LIO static map', '~0.7 M pts'],
        note: 'Clean static map reconstructed online by DOR-LIO. Height-colored.',
      },
      // Add more maps by appending entries here, e.g.
      // { id: 'mall', title: 'Shopping Mall (handheld)', file: 'data/mall.ply', badges: [...] },
    ],

    // Scene pairs shown in the before/after wipe slider.
    compare: [
      {
        id: 'campus-demo',
        title: 'Campus — dynamic pedestrian removal',
        raw: 'data/campus_raw_demo.ply',
        clean: 'data/campus_clean.ply',
        leftLabel: 'Raw accumulation',
        rightLabel: 'DOR-LIO (Ours)',
        note: 'Demo pair: the static geometry is a real DOR-LIO map; walking ' +
              'pedestrians are synthesized placeholders (red) standing in for a ' +
              'FAST-LIO2 raw export. Replace with real raw/clean pairs anytime — ' +
              'see README.md.',
      },
    ],
  };

  global.DOR_SCENES = SCENES;
})(window);
