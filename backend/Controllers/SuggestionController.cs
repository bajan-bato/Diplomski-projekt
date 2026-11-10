using System;
using backend.Data;
using backend.Mappers;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace backend.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class SuggestionController : ControllerBase
    {
        private readonly AppDbContext ctx;

        public SuggestionController(AppDbContext ctx)
        {
            this.ctx = ctx;
        }

        [HttpGet]
        public async Task<IActionResult> GetAllSuggestions()
        {
            var suggestions = await ctx.Suggestions.Select(s => s.ToSuggestionDTO()).ToListAsync();

            return Ok(suggestions);
        }

        [HttpGet("{id}")]
        public async Task<IActionResult> GetSuggestionById(int id)
        {
            var suggestion = await ctx.Suggestions.Where(s => s.Suggestionid == id).Select(s => s.ToSuggestionDTO()).FirstOrDefaultAsync();

            if (suggestion == null)
            {
                return NotFound();
            }

            return Ok(suggestion);
        }
    }
}
