# Three.js browser dependency

Pinned upstream npm package `three@0.180.0`, from https://registry.npmjs.org/three/-/three-0.180.0.tgz.

Included files: build/three.module.js, build/three.core.js, examples/jsm/controls/OrbitControls.js, LICENSE. The OrbitControls import `from 'three'` is changed to `from './three.module.js'` for direct same-origin browser modules without an import map or CDN.

Three.js is MIT licensed; the upstream license is retained. The browser server exposes only the three JavaScript files explicitly, with the existing same-origin CSP. No CDN, external textures, model downloads, data uploads or package installation is required at demo time.
