use crate::{
    error::{Result, ViewerError},
    volume::Volume,
};

impl Volume {
    // Axial planes borrow contiguous RAS-order memory; no full-volume cloning.
    pub fn axial(&self, index: usize) -> Result<&[f32]> {
        if index >= self.depth {
            return Err(ViewerError("invalid slice index"));
        }
        let size = self.width * self.height;
        Ok(&self.voxels[index * size..(index + 1) * size])
    }
}
