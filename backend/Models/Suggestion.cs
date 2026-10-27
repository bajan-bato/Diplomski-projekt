using System;
using System.Collections.Generic;

namespace backend.Models;

public partial class Suggestion
{
    public int Suggestionid { get; set; }

    public string Text { get; set; } = null!;

    public string Title { get; set; } = null!;

    public DateTime Datetime { get; set; }

    public string Packageid { get; set; } = null!;

    public virtual ICollection<Issue> Issues { get; set; } = new List<Issue>();

    public virtual Package Package { get; set; } = null!;
}
