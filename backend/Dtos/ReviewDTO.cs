using System.Net.NetworkInformation;

namespace backend.Dtos
{
    public class ReviewDTO
    {
        public int status { get; set; }
        public int issueId { get; set; }
        public int analysisId { get; set; }
    }
}
