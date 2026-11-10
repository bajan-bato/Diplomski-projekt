using backend.Models;

namespace backend.Dtos
{
    public class SuggestionDTO
    {
        public int suggestionId { get; set; }
        public string text { get; set; } = null!;
        public string title { get; set; } = null!;
        public DateTime datetime { get; set; }
        public string packageId { get; set; } = null!;
    }
}
