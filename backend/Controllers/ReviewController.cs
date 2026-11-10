using backend.Data;
using backend.Mappers;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace backend.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class ReviewController : ControllerBase
    {
        private readonly AppDbContext ctx;

        public ReviewController(AppDbContext ctx)
        {
            this.ctx = ctx;
        }

        [HttpGet]
        public async Task<IActionResult> GetAllReviews([FromQuery] int? issueId, [FromQuery] int? analysisId)
        {
            var reviews = await ctx.Reviews.Where(r => r.Issueid == issueId && r.Analysisid == analysisId).Select(r => r.ToReviewDTO()).ToListAsync();
            
            return Ok(reviews);
        }
    }
}
