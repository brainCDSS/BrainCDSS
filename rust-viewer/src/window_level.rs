use crate::error::{Result, ViewerError};

pub fn validate(window: f32, level: f32) -> Result<()> {
    if !window.is_finite() || window <= 0.0 || !level.is_finite() {
        return Err(ViewerError(
            "window must be positive and window/level must be finite",
        ));
    }
    Ok(())
}
pub fn intensity(value: f32, window: f32, level: f32) -> u8 {
    (((value - (level - window / 2.0)) / window).clamp(0.0, 1.0) * 255.0).round() as u8
}
pub fn apply(slice: &[f32], window: f32, level: f32) -> Result<Vec<u8>> {
    validate(window, level)?;
    Ok(slice.iter().map(|v| intensity(*v, window, level)).collect())
}
