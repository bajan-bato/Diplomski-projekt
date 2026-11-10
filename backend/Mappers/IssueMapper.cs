using backend.Dtos;
using backend.Models;

namespace backend.Mappers
{
    public static class IssueMapper
    {
        public static IssueDTO ToIssueDTO(this Issue issue)
        {
            return new IssueDTO
            {
                issueId = issue.Issueid,
                text = issue.Text,
                suggestionId = issue.Suggestionid
            };
        }
    }
}
