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

    // Mall 01: display exports only; original maps and metrics remain unchanged.
    compare: [
      {
        id: 'mall01-fastlio2',
        title: 'Mall 01 · DOR-LIO vs FAST-LIO2',
        raw: 'data/mall01/ours.ply',
        clean: 'data/mall01/fastlio2.ply',
        leftLabel: 'DOR-LIO (Ours)',
        rightLabel: 'FAST-LIO2',
        note: 'Mall 01 / floor1. Archived DOR-LIO map vs the September 11 FAST-LIO2 full accumulation. ' +
              'Downsampled for display, with shared height colors and rigid display alignment. ' +
              'Separate runs; differences include estimation and sampling effects.',
      },
      {
        id: 'mall01-btsa',
        title: 'Mall 01 · DOR-LIO vs BTSA',
        raw: 'data/mall01/ours.ply',
        clean: 'data/mall01/btsa.ply',
        leftLabel: 'DOR-LIO (Ours)',
        rightLabel: 'BTSA',
        note: 'Mall 01 / floor1. Archived DOR-LIO map vs BTSA static output (registered points minus detected dynamic points). ' +
              'Downsampled with shared height colors; rigidly aligned for viewing only. ' +
              'A static-map output can still contain dynamic remnants.',
      },
      {
        id: 'mall01-dufomap',
        title: 'Mall 01 · DOR-LIO vs FAST-LIO2 + DUFOMap',
        raw: 'data/mall01/ours.ply',
        clean: 'data/mall01/dufomap.ply',
        leftLabel: 'DOR-LIO (Ours)',
        rightLabel: 'FAST-LIO2 + DUFOMap',
        note: 'Mall 01 / floor1. DUFOMap filters the same FAST-LIO2 run shown on page 1. ' +
              'Both use exactly the same rigid display transform. Shared height colors and display downsampling; ' +
              'no ground-truth dynamic labels are implied.',
      },
    ],
  };

  global.DOR_SCENES = SCENES;
})(window);
