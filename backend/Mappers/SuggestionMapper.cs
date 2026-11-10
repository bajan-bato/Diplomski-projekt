using backend.Dtos;
using backend.Models;

namespace backend.Mappers
{
    public static class SuggestionMapper
    {
        public static SuggestionDTO ToSuggestionDTO(this Suggestion suggestion)
        {
            return new SuggestionDTO
            {
                suggestionId = suggestion.Suggestionid,
                text = suggestion.Text,
                title = suggestion.Title,
                datetime = suggestion.Datetime,
                packageId = suggestion.Packageid
            };
        }
    }
}
