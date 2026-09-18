# Rust/WASM Medical Viewer Beta core

`WasmVolume` owns a RAS-ordered `Vec<f32>` source volume and optional mask and
probability volumes. React copies each decoded NIfTI into WASM once. Slice moves
then borrow the stored volume and allocate only the returned slice/RGBA buffer.

The crate performs axial extraction, window/level conversion, red segmentation
blending and the existing 0.15–1 probability display mapping. It does not define
a diagnostic threshold. NIfTI parsing, affine-to-RAS conversion, Canvas rendering
and interaction stay in the frontend.
