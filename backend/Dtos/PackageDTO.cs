using backend.Models;

namespace backend.Dtos
{
    public class PackageDTO
    {
        public string packageId { get; set; } = null!;
        public string title { get; set; } = null!;
        public string description { get; set; } = null!;
        public string url { get; set; } = null!;
    }
}
