using backend.Models;

namespace backend.Dtos
{
    public class IssueDTO
    {
        public int issueId { get; set; }
        public string text { get; set; } = null!;
        public int suggestionId { get; set; }
    }
}
