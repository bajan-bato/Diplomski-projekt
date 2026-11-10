using backend.Data;
using backend.Mappers;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace backend.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class AnalysisController : ControllerBase
    {
        private readonly AppDbContext ctx;

        public AnalysisController(AppDbContext ctx)
        {
            this.ctx = ctx;
        }

        [HttpGet]
        public async Task<IActionResult> GetAllAnalyses()
        {
            var analyses = await ctx.Analyses.Select(a => a.ToAnalysisDTO()).ToListAsync();

            return Ok(analyses);
        }

        [HttpGet("{id}")]
        public async Task<IActionResult> GetAnalysisById(int id)
        {
            var analysis = await ctx.Analyses.Where(a => a.Analysisid == id).Select(a => a.ToAnalysisDTO()).FirstOrDefaultAsync();
            
            if (analysis == null)
            {
                return NotFound();
            }
            
            return Ok(analysis);
        }
    }
}
