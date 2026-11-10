using backend.Dtos;
using backend.Models;

namespace backend.Mappers
{
    public static class AnalysisMapper
    {
        public static AnalysisDTO ToAnalysisDTO(this Analysis analysis)
        {
            return new AnalysisDTO
            {
                analysisId = analysis.Analysisid,
                datetime = analysis.Datetime,
                idPrev = analysis.Idprev,
                idNext = analysis.Idnext
            };
        }
    }
}
