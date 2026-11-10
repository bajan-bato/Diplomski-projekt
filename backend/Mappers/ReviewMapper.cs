using backend.Dtos;
using backend.Models;

namespace backend.Mappers
{
    public static class ReviewMapper
    {
        public static ReviewDTO ToReviewDTO(this Review review)
        {
            return new ReviewDTO
            {
                status = review.Status,
                issueId = review.Issueid,
                analysisId = review.Analysisid
            };
        }
    }
}
