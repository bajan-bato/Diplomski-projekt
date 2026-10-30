using System;
using System.Collections.Generic;

namespace backend.Models;

public partial class Resource
{
    public string Resourceid { get; set; } = null!;

    public string Format { get; set; } = null!;

    public string Url { get; set; } = null!;

    public string Packageid { get; set; } = null!;

    public virtual Package Package { get; set; } = null!;
}
