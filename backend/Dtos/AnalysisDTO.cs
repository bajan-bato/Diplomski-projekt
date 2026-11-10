using backend.Models;

namespace backend.Dtos
{
    public class AnalysisDTO
    {
        public int analysisId { get; set; }
        public DateTime datetime { get; set; }
        public int? idPrev { get; set; }
        public int? idNext { get; set; }
    }
}
