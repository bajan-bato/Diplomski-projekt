using System;
using System.Collections.Generic;

namespace backend.Models;

public partial class Analysis
{
    public int Analysisid { get; set; }

    public DateTime Datetime { get; set; }

    public int? Idprev { get; set; }

    public int? Idnext { get; set; }

    public virtual Analysis? NextAnalysis { get; set; }

    public virtual Analysis? PreviousAnalysis { get; set; }

    public virtual ICollection<Review> Reviews { get; set; } = new List<Review>();
}
