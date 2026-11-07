using System;
using System.Collections.Generic;

namespace backend.Models;

public partial class Package
{
    public string Packageid { get; set; } = null!;

    public string Title { get; set; } = null!;

    public string Description { get; set; } = null!;

    public string Url { get; set; } = null!;

    public virtual ICollection<Resource> Resources { get; set; } = new List<Resource>();

    public virtual ICollection<Suggestion> Suggestions { get; set; } = new List<Suggestion>();
}
