using backend.Data;
using backend.Mappers;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace backend.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class IssueController : ControllerBase
    {
        private readonly AppDbContext ctx;

        public IssueController(AppDbContext ctx)
        {
            this.ctx = ctx;
        }

        [HttpGet]
        public async Task<IActionResult> GetAllIssues([FromQuery] int? suggestionId)
        {
            var issues = await ctx.Issues.Where(i => i.Suggestionid == suggestionId).Select(i => i.ToIssueDTO()).ToListAsync();
            
            return Ok(issues);
        }
    }
}
