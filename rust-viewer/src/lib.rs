mod error;
mod overlay;
mod slice;
mod volume;
mod window_level;

use error::{Result, ViewerError};
use volume::Volume;
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub struct WasmVolume {
    source: Volume,
    mask: Option<Volume>,
    probability: Option<Volume>,
}
fn js_error(error: ViewerError) -> JsValue {
    JsValue::from_str(&error.to_string())
}

impl WasmVolume {
    fn attach(
        &self,
        width: usize,
        height: usize,
        depth: usize,
        voxels: Vec<f32>,
        probability: bool,
    ) -> Result<Volume> {
        let volume = Volume::new(width, height, depth, voxels)?;
        if !self.source.matches(&volume) {
            return Err(ViewerError("overlay dimensions mismatch"));
        }
        if probability && volume.voxels.iter().any(|v| !(0.0..=1.0).contains(v)) {
            return Err(ViewerError("probability values must be normalized to 0..1"));
        }
        Ok(volume)
    }
}
#[wasm_bindgen]
impl WasmVolume {
    #[wasm_bindgen(constructor)]
    pub fn new(
        width: usize,
        height: usize,
        depth: usize,
        voxels: Vec<f32>,
    ) -> std::result::Result<WasmVolume, JsValue> {
        Ok(Self {
            source: Volume::new(width, height, depth, voxels).map_err(js_error)?,
            mask: None,
            probability: None,
        })
    }
    pub fn set_mask(
        &mut self,
        width: usize,
        height: usize,
        depth: usize,
        voxels: Vec<f32>,
    ) -> std::result::Result<(), JsValue> {
        self.mask = Some(
            self.attach(width, height, depth, voxels, false)
                .map_err(js_error)?,
        );
        Ok(())
    }
    pub fn set_probability(
        &mut self,
        width: usize,
        height: usize,
        depth: usize,
        voxels: Vec<f32>,
    ) -> std::result::Result<(), JsValue> {
        self.probability = Some(
            self.attach(width, height, depth, voxels, true)
                .map_err(js_error)?,
        );
        Ok(())
    }
    pub fn extract_axial_slice(&self, index: usize) -> std::result::Result<Vec<f32>, JsValue> {
        Ok(self.source.axial(index).map_err(js_error)?.to_vec())
    }
    pub fn window_slice(
        &self,
        index: usize,
        window: f32,
        level: f32,
    ) -> std::result::Result<Vec<u8>, JsValue> {
        window_level::apply(self.source.axial(index).map_err(js_error)?, window, level)
            .map_err(js_error)
    }
    pub fn segmentation_slice(
        &self,
        index: usize,
        opacity: f32,
    ) -> std::result::Result<Vec<u8>, JsValue> {
        let volume = self
            .mask
            .as_ref()
            .ok_or_else(|| js_error(ViewerError("segmentation is unavailable")))?;
        overlay::segmentation(volume.axial(index).map_err(js_error)?, opacity).map_err(js_error)
    }
    pub fn probability_slice(
        &self,
        index: usize,
        opacity: f32,
        lut: &[u8],
    ) -> std::result::Result<Vec<u8>, JsValue> {
        let volume = self
            .probability
            .as_ref()
            .ok_or_else(|| js_error(ViewerError("probability is unavailable")))?;
        overlay::probability(volume.axial(index).map_err(js_error)?, opacity, lut).map_err(js_error)
    }
    pub fn render_slice(
        &self,
        index: usize,
        window: f32,
        level: f32,
        mask_opacity: f32,
        probability_opacity: f32,
        lut: &[u8],
    ) -> std::result::Result<Vec<u8>, JsValue> {
        window_level::validate(window, level).map_err(js_error)?;
        overlay::validate_opacity(mask_opacity).map_err(js_error)?;
        overlay::validate_opacity(probability_opacity).map_err(js_error)?;
        if lut.len() != 1024 {
            return Err(js_error(ViewerError("invalid probability colormap")));
        }
        let source = self.source.axial(index).map_err(js_error)?;
        let mask = self
            .mask
            .as_ref()
            .map(|v| v.axial(index))
            .transpose()
            .map_err(js_error)?;
        let probability = self
            .probability
            .as_ref()
            .map(|v| v.axial(index))
            .transpose()
            .map_err(js_error)?;
        let mut rgba = vec![0; source.len() * 4];
        for (i, pixel) in rgba.as_chunks_mut::<4>().0.iter_mut().enumerate() {
            let gray = window_level::intensity(source[i], window, level);
            pixel.copy_from_slice(&[gray, gray, gray, 255]);
            if let Some(values) = probability {
                if values[i] >= 0.15 {
                    let offset =
                        (((values[i] - 0.15) / 0.85).clamp(0.0, 1.0) * 255.0).round() as usize * 4;
                    overlay::blend(pixel, &lut[offset..offset + 3], probability_opacity);
                }
            }
            if let Some(values) = mask {
                if values[i] >= 0.5 {
                    overlay::blend(pixel, &[255, 0, 0], mask_opacity);
                }
            }
        }
        Ok(rgba)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn fixture() -> Volume {
        Volume::new(2, 2, 3, (0..12).map(|v| v as f32).collect()).expect("synthetic fixture")
    }
    #[test]
    fn dimensions_and_empty_buffer() {
        assert!(Volume::new(0, 2, 3, vec![]).is_err());
        assert!(Volume::new(2, 2, 3, vec![]).is_err());
        assert!(Volume::new(usize::MAX, 2, 3, vec![]).is_err());
        assert!(Volume::new(1, 1, 1, vec![f32::NAN]).is_err());
    }
    #[test]
    fn first_middle_last_axial() {
        let v = fixture();
        assert_eq!(v.axial(0).expect("first"), &[0., 1., 2., 3.]);
        assert_eq!(v.axial(1).expect("middle"), &[4., 5., 6., 7.]);
        assert_eq!(v.axial(2).expect("last"), &[8., 9., 10., 11.]);
        assert!(v.axial(3).is_err());
    }
    #[test]
    fn window_level_mapping() {
        assert_eq!(
            window_level::apply(&[-20., 0., 40., 80., 100.], 80., 40.).expect("mapping"),
            vec![0, 0, 128, 255, 255]
        );
        assert!(window_level::apply(&[0.], 0., 0.).is_err());
    }
    #[test]
    fn segmentation_opacity() {
        assert_eq!(
            overlay::segmentation(&[0., 1.], 0.5).expect("overlay"),
            vec![255, 0, 0, 0, 255, 0, 0, 128]
        );
        assert!(overlay::segmentation(&[1.], 1.1).is_err());
    }
    #[test]
    fn probability_normalization_and_dimensions() {
        let v = WasmVolume {
            source: fixture(),
            mask: None,
            probability: None,
        };
        assert!(v.attach(2, 2, 2, vec![0.; 8], false).is_err());
        assert!(v.attach(2, 2, 2, vec![0.; 8], true).is_err());
        assert!(v.attach(2, 2, 3, vec![1.1; 12], true).is_err());
        assert!(v.attach(2, 2, 3, vec![0.5; 12], true).is_ok());
        assert!(overlay::probability(&[0.], 1., &[0; 4]).is_err());
        let lut = vec![100; 1024];
        let output = overlay::probability(&[0., 0.15, 1.], 0.5, &lut).expect("overlay");
        assert_eq!([output[3], output[7], output[11]], [0, 128, 128]);
    }
}
