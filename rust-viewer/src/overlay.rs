use crate::error::{Result, ViewerError};

pub fn validate_opacity(opacity: f32) -> Result<()> {
    if !opacity.is_finite() || !(0.0..=1.0).contains(&opacity) {
        return Err(ViewerError("opacity must be between 0 and 1"));
    }
    Ok(())
}
pub fn blend(pixel: &mut [u8], color: &[u8], opacity: f32) {
    for channel in 0..3 {
        pixel[channel] = (pixel[channel] as f32 * (1.0 - opacity) + color[channel] as f32 * opacity)
            .round() as u8;
    }
}
pub fn segmentation(slice: &[f32], opacity: f32) -> Result<Vec<u8>> {
    validate_opacity(opacity)?;
    Ok(slice
        .iter()
        .flat_map(|v| {
            [
                255,
                0,
                0,
                if *v >= 0.5 {
                    (opacity * 255.0).round() as u8
                } else {
                    0
                },
            ]
        })
        .collect())
}
pub fn probability(slice: &[f32], opacity: f32, lut: &[u8]) -> Result<Vec<u8>> {
    validate_opacity(opacity)?;
    if lut.len() != 1024 {
        return Err(ViewerError(
            "probability colormap must contain 256 RGBA entries",
        ));
    }
    // 0.15 is the existing viewer's display floor, not a diagnostic threshold.
    Ok(slice
        .iter()
        .flat_map(|v| {
            let offset = (((*v - 0.15) / 0.85).clamp(0.0, 1.0) * 255.0).round() as usize * 4;
            [
                lut[offset],
                lut[offset + 1],
                lut[offset + 2],
                if *v >= 0.15 {
                    (opacity * 255.0).round() as u8
                } else {
                    0
                },
            ]
        })
        .collect())
}
