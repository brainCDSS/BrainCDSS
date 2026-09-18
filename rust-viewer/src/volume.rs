use crate::error::{Result, ViewerError};

pub struct Volume {
    pub width: usize,
    pub height: usize,
    pub depth: usize,
    pub voxels: Vec<f32>,
}
impl Volume {
    pub fn new(width: usize, height: usize, depth: usize, voxels: Vec<f32>) -> Result<Self> {
        if width == 0 || height == 0 || depth == 0 {
            return Err(ViewerError(
                "invalid dimensions: all dimensions must be positive",
            ));
        }
        let length = width
            .checked_mul(height)
            .and_then(|n| n.checked_mul(depth))
            .ok_or(ViewerError("invalid dimensions: size overflow"))?;
        if voxels.len() != length {
            return Err(ViewerError("volume length mismatch"));
        }
        if voxels.iter().any(|v| !v.is_finite()) {
            return Err(ViewerError("volume contains non-finite voxels"));
        }
        Ok(Self {
            width,
            height,
            depth,
            voxels,
        })
    }
    pub fn matches(&self, other: &Self) -> bool {
        self.width == other.width && self.height == other.height && self.depth == other.depth
    }
}
