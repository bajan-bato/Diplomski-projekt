using System;

namespace backend.Controllers
{
	[ApiController]
	[Route("api/[controller]")]
    public class SuggestionController : ControllerBase
    {
		private readonly DbContext ctx;
		
		public SuggestionController(DbContext ctx)
		{
			this.ctx = ctx;
		}

		[HttpGet]
		public async Task<IActionResult> Get()
		{
			var suggestions = await ctx.Suggestions.ToListAsync();

			return Ok(suggestions);
        }

		[HttpGet("{id}")]
        public async Task<IActionResult> Get(int id)
        {
            var suggestion = await ctx.Suggestions.FindAsync(id);

            if (suggestion == null)
            {
                return NotFound();
            }
            
			return Ok(suggestion);
        }
    }
