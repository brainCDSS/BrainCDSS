use std::fmt;

#[derive(Debug, PartialEq)]
pub struct ViewerError(pub &'static str);
impl fmt::Display for ViewerError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.0)
    }
}
impl std::error::Error for ViewerError {}
pub type Result<T> = std::result::Result<T, ViewerError>;
