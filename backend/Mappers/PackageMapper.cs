using backend.Dtos;
using backend.Models;

namespace backend.Mappers
{
    public static class PackageMapper
    {
        public static PackageDTO ToPackageDTO(this Package package)
        {
            return new PackageDTO
            {
                packageId = package.Packageid,
                title = package.Title,
                description = package.Description,
                url = package.Url
            };
        }
    }
}
