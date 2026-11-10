using backend.Data;
using backend.Mappers;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace backend.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class PackageController : ControllerBase
    {
        private readonly AppDbContext ctx;

        public PackageController(AppDbContext ctx)
        {
            this.ctx = ctx;
        }

        [HttpGet]
        public async Task<IActionResult> GetAllPackages()
        {
            var packages = await ctx.Packages.Select(p => p.ToPackageDTO()).ToListAsync();

            return Ok(packages);
        }

        [HttpGet("{id}")]
        public async Task<IActionResult> GetPackageById(string id)
        {
            var package = await ctx.Packages.Where(p => p.Packageid == id).Select(p => p.ToPackageDTO()).FirstOrDefaultAsync();

            if (package == null)
            {
                return NotFound();
            }

            return Ok(package);
        }
    }
}
